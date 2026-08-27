"""One-off migration: strip promotional/marketing decorations from product_name across
전체 제품 — 원래 8개 브랜드(더마토리·메디힐·넘버즈인·닥터지·아떼·성분에디터·아비브·어퓨)에만
적용하던 걸 전체 DB로 확장했다.

제거 대상:
  - 앞에 붙는 대괄호 태그(예: "[NEW]", "[단독기획]", "[모공고민|화잘먹]") — 하나 이상 연속.
  - 여는 대괄호 없이 "...] "로 시작하는, 스크래핑 과정에서 잘린 태그
    (예: "10겹장벽크림] 닥터자르트...", "] 에스트라...").
  - 끝에 남는, 닫는 대괄호 없이 잘린 여는 태그(예: "...크림 [단품/증정기획").
  - 끝에 붙는 "~기획" 문구 — 앞에 알려진 프로모션 수식어(리필/더블/단품/증정/단독/대용량/
    한정/N입/N+N 등)가 붙어있으면 그것까지 같이 제거하고, 뒤에 딸려오는 번들 구성 괄호
    (닫는 괄호 없이 잘린 경우 포함)나 "/단품"류 접미사도 함께 제거한다.
    주의: 프로모션 수식어는 화이트리스트로만 매칭한다 — "카밍 기획"처럼 실제 제품 설명
    단어가 우연히 "기획" 바로 앞에 올 수도 있어서, 무작정 앞의 한글 n글자를 지우면
    진짜 제품명 일부가 날아간다(예: "하이드라 카밍 기획(50ml+15ml)" → "카밍"까지 지우면 안 됨).
  - 끝에 남는 낱개 기호(*, • 등 스크래핑 잔여물).

product_id는 안 바뀌므로 이미지/성분계열 큐레이션 등 다른 테이블 연결은 영향 없다.

Usage:
    python -m scripts.clean_product_names            # dry-run (미리보기만, DB 안 바뀜)
    python -m scripts.clean_product_names --apply     # 실제 반영
    python -m scripts.clean_product_names --brands 더마토리 메디힐   # 특정 브랜드만
    python -m scripts.clean_product_names --db-url URL --apply
"""

import argparse
import re

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.product import Product

_LEADING_BRACKET_RE = re.compile(r"^(\[[^\]]*\]\s*)+")
# 여는 대괄호 없이 "...] " 형태로 시작하는, 잘린 태그(예: "트러블손절크림] 넘버즈인...",
# "] 에스트라..." 처럼 태그 내용이 아예 없이 잘린 경우도 포함).
_ORPHAN_CLOSE_BRACKET_RE = re.compile(r"^[^\[\]]{0,30}\]\s*")
# 끝에 닫는 대괄호 없이 잘린, 열린 태그(예: "...크림 [단품/증정기획").
_TRAILING_OPEN_BRACKET_RE = re.compile(r"\s*\[[^\[\]]{0,40}$")

# "기획" 바로 앞에 붙을 수 있는, 알려진 프로모션 수식어만 화이트리스트로 인정한다.
# (임의의 한글 n글자를 지우면 "카밍 기획"의 "카밍"처럼 진짜 제품 설명이 날아갈 수 있어서)
_PROMO_QUALIFIER = (
    r"(?:리필|더블|단품|증정|단독|대용량|한정|스페셜|기획전|사은품|덤|본품|"
    r"[0-9]+\s*\+\s*[0-9]+|[0-9]+입)"
)
# 예: " 기획", " 리필 기획", " 더블 기획 (200ml+200ml)", " 1+1 기획(+손거울 증정)",
# " 기획/단품", " 기획 (" (닫는 괄호 없이 잘린 원본 데이터).
_TRAILING_PROMO_RE = re.compile(
    rf"\s*(?:{_PROMO_QUALIFIER}\s*){{0,2}}"
    r"기획"
    r"(?:\s*/\s*(?:단품|리필|증정))?"
    r"\s*\(?[^()]*\)?\s*$"
)
_TRAILING_SYMBOL_RE = re.compile(r"\s*[*•·]+\s*$")
_WHITESPACE_RE = re.compile(r"\s{2,}")


def clean_name(name: str) -> str:
    cleaned = _LEADING_BRACKET_RE.sub("", name)
    cleaned = _ORPHAN_CLOSE_BRACKET_RE.sub("", cleaned)
    cleaned = _TRAILING_OPEN_BRACKET_RE.sub("", cleaned)
    cleaned = _TRAILING_PROMO_RE.sub("", cleaned)
    cleaned = _TRAILING_SYMBOL_RE.sub("", cleaned)
    cleaned = _WHITESPACE_RE.sub(" ", cleaned).strip()
    return cleaned


def run(db_url: str, apply: bool, brands: list[str] | None) -> None:
    engine = create_engine(db_url)
    with Session(engine) as session:
        stmt = select(Product).order_by(Product.brand, Product.product_name)
        if brands:
            stmt = stmt.where(Product.brand.in_(brands))
        products = session.scalars(stmt).all()

        # (brand, cleaned_name)이 이미 DB에 있거나(다른 product_id), 이번 배치 안에서 두 번
        # 나오면 UNIQUE(brand, product_name) 제약 위반 — 사실상 같은 제품이 프로모션 태그만
        # 다르게 붙어 중복 등록된 경우다. 어느 쪽을 지울지는 판단할 근거가 없어서(이미지/성분계열
        # 연결이 다를 수 있음) 자동 삭제하지 않고, 이런 행은 이름 정리에서 제외하고 따로 보고한다.
        all_by_brand_name: dict[tuple[str, str], list[str]] = {}
        for p in session.scalars(select(Product)).all():
            all_by_brand_name.setdefault((p.brand, p.product_name), []).append(p.product_id)

        target_names: dict[tuple[str, str], list[str]] = {}
        for p in products:
            cleaned = clean_name(p.product_name)
            if cleaned == p.product_name:
                continue
            key = (p.brand, cleaned)
            target_names.setdefault(key, []).append(p.product_id)
            existing = all_by_brand_name.get(key, [])
            for other_id in existing:
                if other_id != p.product_id:
                    target_names[key].append(other_id)

        skip_ids = {pid for key, ids in target_names.items() if len(set(ids)) > 1 for pid in ids}

        changed = 0
        skipped = []
        for p in products:
            cleaned = clean_name(p.product_name)
            if cleaned == p.product_name:
                continue
            if p.product_id in skip_ids:
                skipped.append(p)
                continue
            changed += 1
            print(f"[{p.brand}] {p.product_id}")
            print(f"  전: {p.product_name}")
            print(f"  후: {cleaned}")
            if apply:
                p.product_name = cleaned

        if skipped:
            print(f"\n[건너뜀 — 정리하면 같은 브랜드+제품명을 가진 다른 제품과 중복됨, 중복 제품 정리 필요]")
            for p in skipped:
                print(f"  [{p.brand}] {p.product_id}: {p.product_name}  →  {clean_name(p.product_name)}")

        if apply:
            session.commit()
            print(f"\n{changed}/{len(products)}개 변경 완료 (반영됨), {len(skipped)}개 건너뜀")
        else:
            print(f"\n{changed}/{len(products)}개 변경 예정 (dry-run — --apply로 실제 반영), {len(skipped)}개 건너뜀 예정")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-url", default=settings.database_url)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--brands", nargs="+", default=None, help="지정하면 해당 브랜드만 처리 (기본: 전체)")
    args = parser.parse_args()
    run(args.db_url, args.apply, args.brands)
