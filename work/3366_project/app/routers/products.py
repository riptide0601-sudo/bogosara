from datetime import datetime, timezone

import requests
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
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
    ProductSimilarityRead,
)
from app.similarity import DEFAULT_TOP_K, find_similar_products

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


def _build_similar_products(
    product_id: str, db: Session, *, top_k: int, min_score: float, limit: int
) -> list[ProductSimilarityRead]:
    scored = find_similar_products(product_id, db, top_k=top_k, min_score=min_score, limit=limit)
    if not scored:
        return []
    products_by_id = {
        product.product_id: product
        for product in db.scalars(
            select(Product).where(Product.product_id.in_([pid for pid, _ in scored]))
        ).all()
    }
    return [
        ProductSimilarityRead(product=products_by_id[pid], score=score)
        for pid, score in scored
        if pid in products_by_id
    ]


def _to_detail(product: Product, db: Session) -> ProductDetail:
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
    # 유사도 계산(app/similarity.py)과 같은 기준(label_rank 상위 DEFAULT_TOP_K개)으로
    # "주요 성분"을 뽑는다 — ingredients가 이미 label_rank순으로 정렬돼 있어 그대로 슬라이스.
    detail.key_ingredients = detail.ingredients[:DEFAULT_TOP_K]
    # 추천도 같은 key_ingredients 기준(DEFAULT_TOP_K)으로 계산해 이 제품을 볼 때 바로 딸려온다.
    # 사이트에 뜨는 건 확신도가 높은 것만 보여주기 위해 70% 이상만 노출한다.
    detail.similar_products = _build_similar_products(
        product.product_id, db, top_k=DEFAULT_TOP_K, min_score=0.7, limit=10
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
    return _to_detail(product, db)


@router.get("/{product_id}/similar", response_model=list[ProductSimilarityRead])
def get_similar_products(
    product_id: str,
    top_k: int = Query(
        default=DEFAULT_TOP_K, ge=1, description="주요 성분으로 취급할 상위 성분 개수(label_rank 기준)"
    ),
    min_score: float = Query(default=0.5, ge=0.0, le=1.0),
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    if db.get(Product, product_id) is None:
        raise HTTPException(status_code=404, detail="Product not found")

    return _build_similar_products(product_id, db, top_k=top_k, min_score=min_score, limit=limit)


@router.put("/{product_id}/ingredients", status_code=204)
def link_ingredient(
    product_id: str, payload: ProductIngredientLink, db: Session = Depends(get_db)
):
    if db.get(Product, product_id) is None:
        raise HTTPException(status_code=404, detail="Product not found")
    if db.get(Ingredient, payload.ingredient_id) is None:
        raise HTTPException(status_code=404, detail="Ingredient not found")

    stmt = (
        pg_insert(ProductIngredient)
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
