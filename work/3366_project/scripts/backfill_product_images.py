"""One-off migration: add product.image_url column (if missing) and backfill it
by matching app/static/images/products/{product_id}.{ext} filenames to products.

Usage:
    python -m scripts.backfill_product_images [--db-url URL]

Safe to re-run — skips the ALTER TABLE if the column already exists, and only
touches products whose id matches an image file on disk each run.
"""

import argparse
from pathlib import Path

from sqlalchemy import create_engine, inspect, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.product import Product

_IMAGES_DIR = Path(__file__).resolve().parents[1] / "app" / "static" / "images" / "products"
_ALLOWED_EXTS = {".jpg", ".jpeg", ".png", ".webp"}


def _ensure_column(engine) -> None:
    inspector = inspect(engine)
    columns = {col["name"] for col in inspector.get_columns("product")}
    if "image_url" in columns:
        return
    with engine.begin() as conn:
        conn.exec_driver_sql("ALTER TABLE product ADD COLUMN image_url VARCHAR")


def _images_by_product_id() -> dict[str, str]:
    """{product_id: '/images/products/<filename>'} — 파일명(확장자 제외)이 product_id다."""
    mapping: dict[str, str] = {}
    for path in _IMAGES_DIR.iterdir():
        if path.suffix.lower() not in _ALLOWED_EXTS:
            continue
        mapping[path.stem] = f"/images/products/{path.name}"
    return mapping


def backfill(db_url: str) -> None:
    engine = create_engine(db_url)
    _ensure_column(engine)

    images = _images_by_product_id()
    with Session(engine) as session:
        products = session.scalars(
            select(Product).where(Product.product_id.in_(images.keys()))
        ).all()
        for product in products:
            product.image_url = images[product.product_id]
        session.commit()
        print(f"{len(products)}/{len(images)} image files matched to products in {db_url}")
        unmatched = images.keys() - {p.product_id for p in products}
        if unmatched:
            print("no matching product_id for:", ", ".join(sorted(unmatched)))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-url", default=settings.database_url)
    args = parser.parse_args()
    backfill(args.db_url)
