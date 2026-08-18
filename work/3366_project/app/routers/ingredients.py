from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import String, cast, or_, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models.ingredient import Ingredient
from app.models.ingredient_purpose import IngredientPurpose
from app.models.llm_summary import LLMSummary
from app.models.purpose import Purpose
from app.schemas.ingredient import (
    IngredientCreate,
    IngredientDetail,
    IngredientRead,
    IngredientUpdate,
)
from app.schemas.llm_summary import LLMSummaryRead, LLMSummaryUpsert

router = APIRouter(prefix="/ingredients", tags=["ingredients"])


def _detail_query():
    return select(Ingredient).options(
        selectinload(Ingredient.ingredient_purposes).selectinload(IngredientPurpose.purpose),
        selectinload(Ingredient.llm_summary),
    )


def _to_detail(ingredient: Ingredient) -> IngredientDetail:
    detail = IngredientDetail.model_validate(ingredient)
    detail.purposes = [
        ip.purpose for ip in ingredient.ingredient_purposes  # type: ignore[misc]
    ]
    return detail


@router.get("", response_model=list[IngredientDetail])
def list_ingredients(
    query: str | None = Query(default=None, description="name_kr/name_en/synonyms 검색어"),
    db: Session = Depends(get_db),
):
    stmt = _detail_query()
    if query:
        stmt = stmt.where(
            or_(
                Ingredient.name_kr.ilike(f"%{query}%"),
                Ingredient.name_en.ilike(f"%{query}%"),
                cast(Ingredient.synonyms, String).ilike(f'%"{query}"%'),
            )
        )
    ingredients = db.scalars(stmt.order_by(Ingredient.name_kr)).all()
    return [_to_detail(ingredient) for ingredient in ingredients]


@router.post("", response_model=IngredientRead, status_code=201)
def create_ingredient(payload: IngredientCreate, db: Session = Depends(get_db)):
    ingredient = Ingredient(**payload.model_dump())
    db.add(ingredient)
    db.commit()
    db.refresh(ingredient)
    return ingredient


@router.get("/{ingredient_id}", response_model=IngredientDetail)
def get_ingredient(ingredient_id: int, db: Session = Depends(get_db)):
    ingredient = db.scalars(
        _detail_query().where(Ingredient.ingredient_id == ingredient_id)
    ).first()
    if ingredient is None:
        raise HTTPException(status_code=404, detail="Ingredient not found")
    return _to_detail(ingredient)


@router.patch("/{ingredient_id}", response_model=IngredientRead)
def update_ingredient(
    ingredient_id: int, payload: IngredientUpdate, db: Session = Depends(get_db)
):
    ingredient = db.get(Ingredient, ingredient_id)
    if ingredient is None:
        raise HTTPException(status_code=404, detail="Ingredient not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(ingredient, field, value)
    db.commit()
    db.refresh(ingredient)
    return ingredient


@router.put("/{ingredient_id}/purposes/{purpose_id}", status_code=204)
def link_purpose(ingredient_id: int, purpose_id: int, db: Session = Depends(get_db)):
    if db.get(Ingredient, ingredient_id) is None:
        raise HTTPException(status_code=404, detail="Ingredient not found")
    if db.get(Purpose, purpose_id) is None:
        raise HTTPException(status_code=404, detail="Purpose not found")

    stmt = (
        sqlite_insert(IngredientPurpose)
        .values(ingredient_id=ingredient_id, purpose_id=purpose_id)
        .on_conflict_do_nothing(index_elements=["ingredient_id", "purpose_id"])
    )
    db.execute(stmt)
    db.commit()


@router.delete("/{ingredient_id}/purposes/{purpose_id}", status_code=204)
def unlink_purpose(ingredient_id: int, purpose_id: int, db: Session = Depends(get_db)):
    link = db.get(IngredientPurpose, {"ingredient_id": ingredient_id, "purpose_id": purpose_id})
    if link is None:
        raise HTTPException(status_code=404, detail="Link not found")
    db.delete(link)
    db.commit()


@router.get("/{ingredient_id}/llm-summary", response_model=LLMSummaryRead)
def get_llm_summary(ingredient_id: int, db: Session = Depends(get_db)):
    summary = db.get(LLMSummary, ingredient_id)
    if summary is None:
        raise HTTPException(status_code=404, detail="LLM summary not found")
    return summary


@router.put("/{ingredient_id}/llm-summary", response_model=LLMSummaryRead)
def upsert_llm_summary(
    ingredient_id: int, payload: LLMSummaryUpsert, db: Session = Depends(get_db)
):
    if db.get(Ingredient, ingredient_id) is None:
        raise HTTPException(status_code=404, detail="Ingredient not found")

    summary = db.get(LLMSummary, ingredient_id)
    data = payload.model_dump()
    data["summary_generated_at"] = datetime.now(timezone.utc)
    if summary is None:
        summary = LLMSummary(ingredient_id=ingredient_id, **data)
        db.add(summary)
    else:
        for field, value in data.items():
            setattr(summary, field, value)
    db.commit()
    db.refresh(summary)
    return summary
