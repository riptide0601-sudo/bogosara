"""One-off migration: add product.category column (if missing) and backfill it
from product_name via app.product_category.classify().

Usage:
    python -m scripts.backfill_product_category [--db-url URL]

Safe to re-run — skips the ALTER TABLE if the column already exists, and
recomputes every product's category each run (idempotent).
"""

import argparse

from sqlalchemy import create_engine, inspect, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.product import Product
from app.product_category import classify


def _ensure_column(engine) -> None:
    inspector = inspect(engine)
    columns = {col["name"] for col in inspector.get_columns("product")}
    if "category" in columns:
        return
    with engine.begin() as conn:
        conn.exec_driver_sql("ALTER TABLE product ADD COLUMN category VARCHAR")


def backfill(db_url: str) -> None:
    engine = create_engine(db_url)
    _ensure_column(engine)

    with Session(engine) as session:
        products = session.scalars(select(Product)).all()
        for product in products:
            product.category = classify(product.product_name).name
        session.commit()
        print(f"{len(products)} products classified into {db_url}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-url", default=settings.database_url)
    args = parser.parse_args()
    backfill(args.db_url)
