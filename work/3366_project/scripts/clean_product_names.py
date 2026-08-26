"""One-off migration: strip promotional/marketing decorations from product_name for a
given set of brands — leading bracket tags(예: "[화잘먹]", "[단독기획]"), 잘려서 여는
대괄호 없이 남은 태그(예: "트러블손절크림] "), 끝에 붙은 "~기획"류 문구와 그 뒤에 딸려오는
번들 구성 괄호(예: "더블 기획 (200ml+200ml)")를 제거해서 "브랜드 + 제품명 + 용량"만 남긴다.

product_id는 안 바뀌므로 이미지/성분계열 큐레이션 등 다른 테이블 연결은 영향 없다.

Usage:
    python -m scripts.clean_product_names            # dry-run (미리보기만, DB 안 바뀜)
    python -m scripts.clean_product_names --apply     # 실제 반영
    python -m scripts.clean_product_names --db-url URL --apply
"""

import argparse
import re

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.product import Product

BRANDS = ["더마토리", "메디힐", "넘버즈인", "닥터지", "아떼", "성분에디터", "아비브", "어퓨"]

_LEADING_BRACKET_RE = re.compile(r"^(\[[^\]]*\]\s*)+")
# 여는 대괄호 없이 "...] " 형태로 시작하는, 잘린 태그(예: "트러블손절크림] 넘버즈인...").
_ORPHAN_CLOSE_BRACKET_RE = re.compile(r"^[^\[\]]{1,20}\]\s*")
# 끝에 붙는 "~기획" 계열 문구 — 기획 앞에 짧은 수식어(리필/증정/단독/더블/튜브 등, 붙어있든
# 띄어있든)가 있을 수 있고, 뒤에 번들 구성을 적은 괄호(닫는 괄호가 없이 잘린 경우 포함)가
# 딸려올 수 있다. 예: " 기획", " 리필기획", " 증정 기획", " 더블 기획 (200ml+200ml)",
# " 튜브 기획 (" (닫는 괄호 없이 잘린 원본 데이터).
_TRAILING_PROMO_RE = re.compile(r"\s*[가-힣]{0,3}\s*기획\s*\(?[^()]*\)?\s*$")
_WHITESPACE_RE = re.compile(r"\s{2,}")


def clean_name(name: str) -> str:
    cleaned = _LEADING_BRACKET_RE.sub("", name)
    cleaned = _ORPHAN_CLOSE_BRACKET_RE.sub("", cleaned)
    cleaned = _TRAILING_PROMO_RE.sub("", cleaned)
    cleaned = _WHITESPACE_RE.sub(" ", cleaned).strip()
    return cleaned


def run(db_url: str, apply: bool) -> None:
    engine = create_engine(db_url)
    with Session(engine) as session:
        products = session.scalars(
            select(Product).where(Product.brand.in_(BRANDS)).order_by(Product.brand, Product.product_name)
        ).all()

        changed = 0
        for p in products:
            cleaned = clean_name(p.product_name)
            if cleaned != p.product_name:
                changed += 1
                print(f"[{p.brand}] {p.product_id}")
                print(f"  전: {p.product_name}")
                print(f"  후: {cleaned}")
                if apply:
                    p.product_name = cleaned

        if apply:
            session.commit()
            print(f"\n{changed}/{len(products)}개 변경 완료 (반영됨)")
        else:
            print(f"\n{changed}/{len(products)}개 변경 예정 (dry-run — --apply로 실제 반영)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-url", default=settings.database_url)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    run(args.db_url, args.apply)
