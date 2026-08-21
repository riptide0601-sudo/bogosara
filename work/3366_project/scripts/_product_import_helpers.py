"""제품 일괄 임포트 스크립트들이 공유하는 DB 쓰기 헬퍼."""

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.product import Product
from app.models.product_ingredient import ProductIngredient
from app.product_category import classify as classify_category


def find_or_create_product(
    db: Session, product_name: str, brand: str | None = None
) -> tuple[Product, bool]:
    product = db.scalars(select(Product).where(Product.product_name == product_name)).first()
    if product is not None:
        return product, False
    product = Product(
        product_name=product_name,
        brand=brand,
        category=classify_category(product_name).name,
    )
    db.add(product)
    db.flush()
    return product, True


def upsert_product_ingredient(
    db: Session, product_id: str, ingredient_id: int, label_rank: int, matched_text: str
) -> None:
    insert_fn = pg_insert if db.bind.dialect.name == "postgresql" else sqlite_insert
    stmt = (
        insert_fn(ProductIngredient)
        .values(
            product_id=product_id,
            ingredient_id=ingredient_id,
            label_rank=label_rank,
            matched_text=matched_text,
        )
        .on_conflict_do_nothing(index_elements=["product_id", "ingredient_id"])
    )
    db.execute(stmt)
