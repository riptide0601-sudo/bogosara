"""One-off: clean_product_names.py 이후에도 남아있던 개별 케이스들을 정리한다.

1) 이름만 고치면 되는 것들 (NAME_FIXES) — 다른 행과 안 겹침, 단순 UPDATE.
2) 중복 제품 병합 (MERGES) — 정리하면 두 행의 (brand, product_name)이 완전히 똑같아지는
   경우만 병합 대상으로 삼는다("이름이 완전히 같아야만 지운다" 원칙). 이름이 비슷해 보여도
   완전히 똑같지 않으면(예: 닥터지 p-d5b85ccdccef — 공백/용량 차이) 병합하지 않는다.
   병합 시: keep 쪽 이름/카테고리를 확정하고, lose 쪽의 product_ingredient/
   product_family_member/product_concern/saved_result/routine_item을 처리(재연결 필요하면
   재연결, 아니면 그냥 삭제)한 뒤 product 행 자체를 삭제한다.

Usage:
    python -m scripts.fix_product_name_edgecases            # dry-run
    python -m scripts.fix_product_name_edgecases --apply     # 실제 반영
"""

import argparse

from sqlalchemy import create_engine, select, delete, update, func
from sqlalchemy.orm import Session

from app.config import settings
from app.models.product import Product
from app.models.product_ingredient import ProductIngredient
from app.models.product_family_member import ProductFamilyMember
from app.models.product_concern import ProductConcern
from app.models.saved_result import SavedResult
from app.models.routine_item import RoutineItem

# (product_id, 새 이름)
NAME_FIXES = [
    ("p-c6b881dfbfb3", "오휘 프라임AD 디에이징 앰플세럼 20ml"),
    ("p-999a267ac664", "코스알엑스 더 알파 - 알부틴 세럼 50ml"),
    ("p-a132d09aabfa", "디마르3 시그니처 에스투드 프로텍터 모공 앰플 170ml"),
    ("p-01199043d802", "피지오겔 레드수딩 시카밸런스 크림 80ml"),
    ("p-540457092283", "브링그린 티트리 시카 수딩 크림 플러스 100ml"),
    ("p-4c4951c980b7", "어바웃미 숲 진정 수분 크림 80ml"),
    ("p-618a4e380db4", "라네즈 워터뱅크 인텐시브 크림 45ml"),
    ("p-d5b85ccdccef", "닥터지 레드 블레미쉬 클리어 히알 시카수딩 세럼"),
]

# (keep_id, lose_id, keep 쪽에 적용할 이름/카테고리 오버라이드(선택))
MERGES = [
    ("p-c16619816de0", "p-7ce23537a34f", None, None),
    ("p-9a67a9686b21", "p-8c1855c9fb92", None, None),
    ("p-b400dc62b46f", "p-0ef88b31baad", "토리든 밸런스풀 시카 진정 크림 80ml", "크림"),
    ("p-378ec731b832", "p-35fc1e667019", None, None),
    # 닥터지 레드 블레미쉬 클리어 히알 시카 수딩 세럼 — 용량(50ml) 표기 있고 사진도 있는
    # p-8d07a757af76을 남기고, 용량/사진 둘 다 없는 p-d5b85ccdccef를 중복으로 삭제한다.
    # (성분 45개 순서까지 완전히 동일 — 같은 제품 확인됨)
    ("p-8d07a757af76", "p-d5b85ccdccef", None, None),
]


def run(db_url: str, apply: bool) -> None:
    engine = create_engine(db_url)
    with Session(engine) as session:
        print("=== 이름만 고치는 것 ===")
        for pid, new_name in NAME_FIXES:
            p = session.get(Product, pid)
            if p is None:
                print(f"  [경고] {pid} 없음 — 건너뜀")
                continue
            print(f"[{p.brand}] {pid}")
            print(f"  전: {p.product_name}")
            print(f"  후: {new_name}")
            if apply:
                p.product_name = new_name

        print("\n=== 중복 병합 ===")
        for keep_id, lose_id, name_override, category_override in MERGES:
            keep = session.get(Product, keep_id)
            lose = session.get(Product, lose_id)
            if keep is None or lose is None:
                print(f"  [경고] {keep_id} 또는 {lose_id} 없음 — 건너뜀")
                continue

            final_name = name_override or keep.product_name
            print(f"KEEP {keep_id} [{keep.brand}] {keep.product_name!r} -> {final_name!r}")
            print(f"LOSE {lose_id} [{lose.brand}] {lose.product_name!r} (삭제됨)")
            if category_override:
                print(f"  category: {keep.category!r} -> {category_override!r}")

            for table, label in [
                (ProductFamilyMember, "product_family_member"),
                (ProductConcern, "product_concern"),
                (SavedResult, "saved_result"),
                (RoutineItem, "routine_item"),
            ]:
                count = session.scalar(
                    select(func.count()).select_from(table).where(table.product_id == lose_id)
                )
                if count:
                    print(f"  [재연결] {label}: {lose_id} -> {keep_id}")
                    if apply:
                        session.execute(update(table).where(table.product_id == lose_id).values(product_id=keep_id))

            pi_count = session.scalar(
                select(func.count()).select_from(ProductIngredient).where(ProductIngredient.product_id == lose_id)
            )
            if pi_count:
                print(f"  [삭제] product_ingredient: {lose_id}의 성분 연결 행 삭제 (keep 쪽 성분표 사용)")
                if apply:
                    session.execute(delete(ProductIngredient).where(ProductIngredient.product_id == lose_id))

            if apply:
                keep.product_name = final_name
                if category_override:
                    keep.category = category_override
                session.delete(lose)

        if apply:
            session.commit()
            print("\n반영 완료")
        else:
            print("\ndry-run — --apply로 실제 반영")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-url", default=settings.database_url)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    run(args.db_url, args.apply)
