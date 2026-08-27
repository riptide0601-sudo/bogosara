"""One-off migration: create ingredient_family / ingredient_family_member tables
(if missing) and seed keyword-based ingredient families — currently just
히알루론산 계열, used by GET /products/{id}/ingredients/{id}/family-rank.

Usage:
    python -m scripts.backfill_ingredient_families [--db-url URL]

Safe to re-run — create_all skips existing tables, and membership inserts are
skipped for ingredients already in the family.
"""

import argparse

from sqlalchemy import create_engine, or_, select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import Base
from app.models.ingredient import Ingredient
from app.models.ingredient_family import IngredientFamily
from app.models.ingredient_family_member import IngredientFamilyMember

# family_name -> 이름에 이 키워드 중 하나라도 들어가면(name_kr/name_en 둘 다 대조) 그 계열 멤버로 채택.
FAMILIES: dict[str, list[str]] = {
    "히알루론산 계열": ["히알루", "hyaluron"],
    # 판테놀(Panthenol)·덱스판테놀·판토테닉애씨드·~판토테네이트 계열을 통틀어 "비타민 B5"로 묶는다.
    "판토텐산(B5) 계열": ["판테놀", "판토텐", "panthenol", "pantothen"],
    # 아스코빅애씨드/아스코빌 유도체(아스코빌글루코사이드, 마그네슘아스코빌포스페이트 등)를
    # 통틀어 "비타민C 계열"로 묶는다 — 한글 표기가 전부 "아스코"로 시작한다.
    "비타민C 계열": ["아스코", "ascorb"],
    "콜라겐 계열": ["콜라겐", "collagen"],
    "비피다 계열": ["비피다", "bifida"],
    # 병풀추출물(Centella Asiatica Extract) 자체는 원료 추출물이라 범위가 너무 넓어 제외하고,
    # 그 안의 정제된 활성 성분(마데카소사이드/마데카식애씨드/아시아티코사이드류)만 묶는다.
    "마데카소사이드 계열": ["마데카", "아시아틱애씨드", "아시아티코사이드", "madecass", "asiaticoside", "asiatic acid"],
}


def seed(db_url: str) -> None:
    engine = create_engine(db_url)
    Base.metadata.create_all(
        engine, tables=[IngredientFamily.__table__, IngredientFamilyMember.__table__]
    )

    with Session(engine) as session:
        for family_name, keywords in FAMILIES.items():
            family = session.scalar(
                select(IngredientFamily).where(IngredientFamily.family_name == family_name)
            )
            if family is None:
                family = IngredientFamily(family_name=family_name)
                session.add(family)
                session.flush()

            conditions = [Ingredient.name_kr.ilike(f"%{kw}%") for kw in keywords]
            conditions += [Ingredient.name_en.ilike(f"%{kw}%") for kw in keywords]
            matched = session.scalars(select(Ingredient).where(or_(*conditions))).all()

            existing_ids = {
                m.ingredient_id
                for m in session.scalars(
                    select(IngredientFamilyMember).where(
                        IngredientFamilyMember.family_id == family.family_id
                    )
                ).all()
            }
            added = 0
            for ing in matched:
                if ing.ingredient_id in existing_ids:
                    continue
                session.add(
                    IngredientFamilyMember(
                        family_id=family.family_id, ingredient_id=ing.ingredient_id
                    )
                )
                added += 1
            session.commit()
            print(f"{family_name}: matched {len(matched)} ingredients, added {added} new members")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-url", default=settings.database_url)
    args = parser.parse_args()
    seed(args.db_url)
