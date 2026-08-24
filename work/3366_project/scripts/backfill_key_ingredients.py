"""One-off/backfill script: populate product.key_ingredients / product.key_purposes
using app.core_ingredient_selector's DB-driven analysis (analyze_product_from_orm).

Usage:
    python -m scripts.backfill_key_ingredients [--db-url URL]

Safe to re-run — skips the ALTER TABLE if the columns already exist, and recomputes
every product's key_ingredients/key_purposes each run (idempotent). Each column stores
a JSON array string (성분명 목록 / 효능 목록, 각각 최대 5개).
"""

import argparse
import json

from sqlalchemy import create_engine, inspect, select
from sqlalchemy.orm import Session, selectinload

from app.config import settings
from app.core_ingredient_selector import analyze_product_from_orm, load_purpose_db_from_db
from app.models.product import Product
from app.models.product_ingredient import ProductIngredient


def _ensure_columns(engine) -> None:
    inspector = inspect(engine)
    columns = {col["name"] for col in inspector.get_columns("product")}
    with engine.begin() as conn:
        if "key_ingredients" not in columns:
            conn.exec_driver_sql("ALTER TABLE product ADD COLUMN key_ingredients TEXT")
        if "key_purposes" not in columns:
            conn.exec_driver_sql("ALTER TABLE product ADD COLUMN key_purposes TEXT")


def backfill(db_url: str) -> None:
    engine = create_engine(db_url)
    _ensure_columns(engine)

    with Session(engine) as session:
        purpose_db = load_purpose_db_from_db(session)

        products = session.scalars(
            select(Product).options(
                selectinload(Product.product_ingredients).selectinload(
                    ProductIngredient.ingredient
                )
            )
        ).all()

        for product in products:
            result = analyze_product_from_orm(product, purpose_db)
            product.key_ingredients = json.dumps(result["ingredients"], ensure_ascii=False)
            product.key_purposes = json.dumps(result["effects"], ensure_ascii=False)

        session.commit()
        print(f"{len(products)} products updated with key_ingredients/key_purposes in {db_url}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-url", default=settings.database_url)
    args = parser.parse_args()
    backfill(args.db_url)
