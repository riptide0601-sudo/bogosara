"""One-off migration: create product_family_member table (if missing) and seed the
사람이 직접 고른 성분 계열별 비교 대상 제품 목록(FAMILY_PRODUCTS).

ingredient_family_member(성분명 키워드 매칭)만으로 비교 모수를 잡으면 DB 전체에서
그 계열 성분이 조금이라도 들어간 제품까지 다 섞여 순위가 무의미해진다(예: 히알루론산
계열 키워드 매칭만으로는 209개). 그래서 실제 "비슷한 제품과 비교하면" 순위 비교는 이
표에 큐레이션된 제품끼리만 하고, ingredient_family_member는 그 제품 안에서 어떤 성분이
대표 성분인지 찾는 용도로만 쓴다(app/routers/products.py get_product_family_rank 참고).

한 제품이 여러 계열에 동시에 큐레이션될 수 있다(예: 더마토리 히알샷은 히알루론산 계열이자
B5 계열이기도 함) — product_family_member의 PK가 (family_id, product_id)라 자연히 지원된다.

Usage:
    python -m scripts.backfill_product_family [--db-url URL]

Safe to re-run — create_all skips existing tables, membership insert is idempotent.
"""

import argparse

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import Base
from app.models.ingredient_family import IngredientFamily
from app.models.product import Product
from app.models.product_family_member import ProductFamilyMember

# family_name -> 정확한 이름으로 못 찾으면 LIKE 후보가 정확히 하나일 때만 채택(사람이 직접 정한 목록).
FAMILY_PRODUCTS: dict[str, list[str]] = {
    "히알루론산 계열": [
        "아떼 멜레이저 프로그래밍 앰플 10ml",
        "비욘드 엔젤 아쿠아 이온 히알루10% 수분 진정 크림 100ml",
        "구달 어성초 히알루론 수딩 크림 75ml 리필",
        "아비브 히알루로닉 붐 크림 워터튜브 75ml",
        "웰라쥬 리얼 히알루로닉 100 크림 50ml",
        "성분에디터 그린토마토 NMN 포어 리프팅 크림 50ml",
        "토리든 다이브인 저분자 히알루론산 토너 300ml",
        "라로슈포제 히알루 B5 수분탄력 크림 50ml 기획 (+3ml+히알루세럼10ml)",
        "디퍼 히알루론산 히알큐브 수분 토너 300ml",
        "키엘 울트라 퓨어 세럼 히알루로닉애씨드 30ml",
        "밀크터치 서양송악 그린히알루론 6초 수분 크림 50g",
        "더마토리 히알샷 베리어 B5 앰플 50ml",
        "닥터지 레드 블레미쉬 클리어 히알 시카 수딩 세럼 50ml",
        # 아래 19개는 라이브 DB(product_family_member)엔 이미 반영돼 있었지만 이 목록엔 없던
        # 것들 — data/labellens.db 스냅샷과 대조해서 채워 넣었다(팀원이 스크립트 갱신 없이
        # DB에 직접/다른 경로로 추가했던 것으로 보임). 총 13 -> 32개.
        "오어스 히알루론시카 7초 세럼 인 앰플 105ml",
        "한율 쑥히알 세럼 40ml",
        "에스트라 아토베리어365 세라-히알 속수분 앰플 30ml",
        "메디필 히알루론산 레이어 물톡스 앰플 30ml",
        "디오디너리 히알루로닉 애시드 2% + B5 30ml",
        "스튜디오17 워터부스트 히알루론 수분크림 80ml",
        "비욘드 엔젤 아쿠아 이온 히알루 10% 수분 가득 진정 앰플 50ml",
        "토리든 다이브인 저분자 히알루론산 수딩 크림 100ml",
        "웰라쥬 리얼 히알루로닉 블루 100 앰플 100ml",
        "한율 어린쑥 속수분 쑥히알 세럼 40ml",
        "스킨1004 마다가스카르 센텔라 히알루-테카 플럼핑 앰플 50ml",
        "브링그린 대나무 히알루 수분 토너 500mL",
        "더랩바이블랑두 올리고 히알루론산 딥 글로우 세럼 85ml",
        "로벡틴 히알루론산 에센스 180ml",
        "메디큐브 PDRN 핑크 히알루로닉 수분크림 50ml",
        "더 에센셜 바이 아리얼 히알루로닉 13 세럼 60ml",
        "더 에센셜 바이 아리얼 히알루로닉 13 크림 100ml",
        "아누아 피디알엔 히알루론산 캡슐 100 세럼 30mL",
        "믹순 히알레배 포어 버블 세럼 70ml",
    ],
    "판토텐산(B5) 계열": [
        "반코르 덱스판테놀17만ppm 장벽크림",
        "어나더페이스 펩타테놀 수분 밸런스 토너 120ml",
        "키엘 칼렌듈라 꽃잎 크림 50ml",
        "달바 더블 세럼 앤 크림 70g",
        "유세린 울트라센시티브 리페어 세럼 30ml",
        "어바웃미 숲 진정 수분 세럼 50ml",
        "라로슈포제 시카플라스트 로션 B5 판테놀 시카에센스 토너 200ml",
        "스킨앤랩 베리어덤 모이스처 부스팅 토너 300ml",
        "아이소이 모이스춰닥터 장수진 수분토너 130ml",
        "아로셀 시카 리페어 판테놀 앰플 40ml",
        "더마토리 히알샷 베리어 B5 앰플 50ml",
    ],
    "비타민C 계열": [
        "나노레시피 비타민 C 리포좀 앰플 30ml",
        # "더마토리 히알샷 베리어 B5 앰플 50ml" — 잘못 넣은 것으로 확인돼 제외(실제 전성분에 비타민C 계열 성분 없음).
        "아떼 비타 EGF 흔적엔딩 세럼",
        "메디힐 비타민씨 브라이트닝 세럼 40ml",
    ],
    "콜라겐 계열": [
        "바이오힐보 프로바이오덤 콜라겐 리모델링 크림",
        # 실제 전성분표엔 콜라겐 계열 성분이 없지만, 큐레이션은 유지하고 프론트가
        # "콜라겐 계열 성분 비교 데이터가 없어요"로 완곡하게 안내한다(has_data=False).
        "메디힐 콜라겐 탄력 볼륨 세럼 40ml",
        "퍼셀 82% 하이-도즈 펩타이드 콜라겐 앰플 20ml",
        "오드로이 카르노신 콜라겐수 78만ppm 세럼",
        "바이오던스 포어 퍼펙팅 콜라겐 펩타이드 크림 50m",  # DB 원본 표기가 "50ml"이 아니라 "50m"(오탈자)
        "넘버즈인 2번 로즈 PDRN 콜라겐 플럼핑 세럼 30ml",
        "라운드랩 동백 딥 콜라겐 탄력 앰플 30ml",
    ],
    "비피다 계열": [
        "풀리 그린 토마토 세럼 30ml",
        "믹순 마스터 세럼 30ml",
        "마녀공장 비피다 바이옴 콤플렉스 앰플 30ml",
        "넘버즈인 3번 보들보들 퍼스트 결부스팅 토너 200ml",
        "아비브 부활초 비피다 세럼 퍼밍 드롭 50ml",
    ],
    "마데카소사이드 계열": [
        "센텔리안24 엑스퍼트 마데카 멜라 캡처 앰플 맥스 45ml",
        "이니스프리 레티놀 시카 모공 흔적 앰플 30ml",
        "센텔리안24 마데카 수분크림 하이드라 카밍",
        "싸이닉 병풀 피디알엔 PDRN 시카 엔드 수딩 크림 10ml",
        "허블룸 콤부차 플랜트 바이옴 세럼 50ml",
        "라씨엘르 신선초 진정에이징 워터 세럼 30ml",
        "아로셀 시카 리페어 판테놀 앰플 40ml",
        "닥터지 레드 블레미쉬 클리어 모이스처 토너",
        "어퓨 마데카소사이드 테트라좀시카 앰플 50ml",
        "포엘리에 옴므 병풀잎수 86.63% 시카 토너 미스트 100ml",
    ],
}


def _find_product_id(session: Session, name: str) -> str | None:
    exact = session.scalar(select(Product.product_id).where(Product.product_name == name))
    if exact:
        return exact
    # 기획/리필/단품 같은 접미사가 붙은 실제 등록명 대응 — 후보가 정확히 하나일 때만 채택.
    candidates = session.scalars(
        select(Product.product_id).where(Product.product_name.like(f"%{name}%"))
    ).all()
    if len(candidates) == 1:
        return candidates[0]
    return None


def seed(db_url: str) -> None:
    engine = create_engine(db_url)
    Base.metadata.create_all(engine, tables=[ProductFamilyMember.__table__])

    with Session(engine) as session:
        for family_name, product_names in FAMILY_PRODUCTS.items():
            family = session.scalar(
                select(IngredientFamily).where(IngredientFamily.family_name == family_name)
            )
            if family is None:
                print(
                    f"[skip] '{family_name}' family가 없습니다 — "
                    "먼저 scripts/backfill_ingredient_families.py를 실행하세요."
                )
                continue

            existing_ids = {
                m.product_id
                for m in session.scalars(
                    select(ProductFamilyMember).where(
                        ProductFamilyMember.family_id == family.family_id
                    )
                ).all()
            }

            matched, unmatched, added = 0, [], 0
            for name in product_names:
                product_id = _find_product_id(session, name)
                if product_id is None:
                    unmatched.append(name)
                    continue
                matched += 1
                if product_id in existing_ids:
                    continue
                session.add(
                    ProductFamilyMember(family_id=family.family_id, product_id=product_id)
                )
                added += 1

            session.commit()
            print(f"{family_name}: {matched}/{len(product_names)} products matched, {added} newly added")
            if unmatched:
                print("  매칭 실패:", ", ".join(unmatched))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-url", default=settings.database_url)
    args = parser.parse_args()
    seed(args.db_url)
