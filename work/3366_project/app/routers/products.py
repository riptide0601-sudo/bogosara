from datetime import datetime, timezone

import requests
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.llm_client import summarize_product
from app.models.ingredient import Ingredient
from app.models.ingredient_purpose import IngredientPurpose
from app.models.product import Product
from app.models.product_ingredient import ProductIngredient
from app.schemas.ingredient import IngredientDetail
from app.schemas.product import (
    ProductCreate,
    ProductDetail,
    ProductIngredientDetail,
    ProductIngredientLink,
    ProductRead,
)

router = APIRouter(prefix="/products", tags=["products"])


def _detail_query():
    return select(Product).options(
        selectinload(Product.product_ingredients)
        .selectinload(ProductIngredient.ingredient)
        .selectinload(Ingredient.ingredient_purposes)
        .selectinload(IngredientPurpose.purpose),
        selectinload(Product.product_ingredients)
        .selectinload(ProductIngredient.ingredient)
        .selectinload(Ingredient.llm_summary),
    )


def _to_detail(product: Product) -> ProductDetail:
    detail = ProductDetail.model_validate(product)
    detail.ingredients = []
    for pi in sorted(
        product.product_ingredients, key=lambda x: (x.label_rank is None, x.label_rank)
    ):
        ingredient_detail = IngredientDetail.model_validate(pi.ingredient)
        ingredient_detail.purposes = [ip.purpose for ip in pi.ingredient.ingredient_purposes]
        detail.ingredients.append(
            ProductIngredientDetail(
                label_rank=pi.label_rank,
                matched_text=pi.matched_text,
                ingredient=ingredient_detail,
            )
        )
    return detail


@router.get("", response_model=list[ProductRead])
def list_products(
    query: str | None = Query(default=None, description="product_name/brand 검색어"),
    db: Session = Depends(get_db),
):
    stmt = select(Product)
    if query:
        stmt = stmt.where(
            or_(
                Product.product_name.ilike(f"%{query}%"),
                Product.brand.ilike(f"%{query}%"),
            )
        )
    return db.scalars(stmt.order_by(Product.product_name)).all()


@router.post("", response_model=ProductRead, status_code=201)
def create_product(payload: ProductCreate, db: Session = Depends(get_db)):
    product = Product(**payload.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@router.get("/{product_id}", response_model=ProductDetail)
def get_product(product_id: str, db: Session = Depends(get_db)):
    product = db.scalars(_detail_query().where(Product.product_id == product_id)).first()
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return _to_detail(product)


@router.put("/{product_id}/ingredients", status_code=204)
def link_ingredient(
    product_id: str, payload: ProductIngredientLink, db: Session = Depends(get_db)
):
    if db.get(Product, product_id) is None:
        raise HTTPException(status_code=404, detail="Product not found")
    if db.get(Ingredient, payload.ingredient_id) is None:
        raise HTTPException(status_code=404, detail="Ingredient not found")

    stmt = (
        sqlite_insert(ProductIngredient)
        .values(
            product_id=product_id,
            ingredient_id=payload.ingredient_id,
            label_rank=payload.label_rank,
            matched_text=payload.matched_text,
        )
        .on_conflict_do_nothing(index_elements=["product_id", "ingredient_id"])
    )
    db.execute(stmt)
    db.commit()


@router.delete("/{product_id}/ingredients/{ingredient_id}", status_code=204)
def unlink_ingredient(
    product_id: str, ingredient_id: int, db: Session = Depends(get_db)
):
    link = db.get(ProductIngredient, {"product_id": product_id, "ingredient_id": ingredient_id})
    if link is None:
        raise HTTPException(status_code=404, detail="Link not found")
    db.delete(link)
    db.commit()


@router.post("/{product_id}/generate-summary", response_model=ProductRead)
def generate_product_summary(product_id: str, db: Session = Depends(get_db)):
    product = db.scalars(
        _detail_query().where(Product.product_id == product_id)
    ).first()
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    if product.summary:
        return product

    ingredient_names = [
        pi.ingredient.name_kr or pi.ingredient.name_en
        for pi in sorted(
            product.product_ingredients, key=lambda x: (x.label_rank is None, x.label_rank)
        )
        if pi.ingredient.name_kr or pi.ingredient.name_en
    ]
    if not ingredient_names:
        raise HTTPException(
            status_code=422, detail="No ingredients available to summarize"
        )

    try:
        summary_text = summarize_product(product.product_name, ingredient_names)
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"LLM request failed: {e}")

    product.summary = summary_text
    product.summary_generated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(product)
    return product
