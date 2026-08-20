"""One-off loader: import data/성분_관계성.xlsx into the ingredient_relation table.

Usage:
    python -m scripts.load_ingredient_relations [--db-url URL] [--xlsx-path PATH]

Defaults to DATABASE_URL from settings (the live Postgres). Creates the
ingredient_relation table if it doesn't exist yet, adds any ingredient the
sheet references that's missing from the ingredient table, then (re)inserts
every relationship row — safe to re-run after the sheet is updated.
"""

import argparse

import openpyxl
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import Base
from app.models import Ingredient, IngredientRelation

# 시트에 없는 name_en은 채워 넣을 데이터가 없어 name_kr만으로 새 ingredient를 만든다.
# 알려진 예외만 여기 추가한다.
_KNOWN_NAME_EN = {"레티날": "Retinal"}


def load(db_url: str, xlsx_path: str) -> None:
    engine = create_engine(db_url)
    Base.metadata.create_all(engine, tables=[IngredientRelation.__table__])

    rows = list(openpyxl.load_workbook(xlsx_path)["Sheet1"].iter_rows(values_only=True))[1:]

    with Session(engine) as session:
        names = {name for row in rows for name in (row[0], row[1])}
        existing = set(
            session.scalars(select(Ingredient.name_kr).where(Ingredient.name_kr.in_(names)))
        )
        missing = names - existing
        for name in missing:
            session.add(Ingredient(name_kr=name, name_en=_KNOWN_NAME_EN.get(name)))
        if missing:
            session.commit()
            print(f"missing ingredient added: {sorted(missing)}")

        id_by_name = dict(
            session.execute(
                select(Ingredient.name_kr, Ingredient.ingredient_id).where(
                    Ingredient.name_kr.in_(names)
                )
            ).all()
        )

        session.execute(IngredientRelation.__table__.delete())
        session.add_all(
            [
                IngredientRelation(
                    ingredient_a_id=id_by_name[name_a],
                    ingredient_b_id=id_by_name[name_b],
                    relation_type=relation_type,
                    user_message=user_message,
                    evidence=evidence,
                    source=source,
                )
                for name_a, name_b, relation_type, user_message, evidence, source in rows
            ]
        )
        session.commit()
        print(f"{len(rows)} relations loaded into {db_url}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-url", default=settings.database_url)
    parser.add_argument("--xlsx-path", default="data/성분_관계성.xlsx")
    args = parser.parse_args()
    load(args.db_url, args.xlsx_path)
