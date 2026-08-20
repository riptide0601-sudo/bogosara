from datetime import datetime, timezone

import requests
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session, selectinload

from app import fuzzy_match
from app.database import get_db
from app.llm_client import rewrite_description
from app.models.ingredient import Ingredient
from app.models.ingredient_purpose import IngredientPurpose
from app.models.ingredient_relation import IngredientRelation
from app.models.llm_summary import LLMSummary
from app.models.purpose import Purpose
from app.schemas.ingredient import (
    IngredientCreate,
    IngredientDetail,
    IngredientRead,
    IngredientUpdate,
)
from app.schemas.ingredient_relation import IngredientRelationRead
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


def search_ingredient_ids(query: str, db: Session) -> list[int]:
    """검색어와 매칭되는 ingredient_id 목록을 우선순위대로 반환합니다.

    검색창·OCR 매칭 등 성분명 매칭이 필요한 모든 곳에서 공유하는 알고리즘입니다.
    1) name_kr/name_en/synonyms substring 매칭 우선 — 이때 이름이 검색어와 정확히
       일치하는 항목을 먼저 배치한다 (예: 검색어 "잔탄검"이 "잔탄검"과 "데하이드로잔탄검"에
       둘 다 substring으로 걸릴 때, 알파벳순만으로는 후자가 앞에 와 버리는 문제 방지)
    2) 매칭이 없으면 자모 기반 fuzzy 매칭으로 폴백 (오타·OCR 오독 대응,
       예: "나이아신아미드" -> "나이아신아마이드")
    """
    exact_match = or_(
        func.lower(Ingredient.name_kr) == query.lower(),
        func.lower(Ingredient.name_en) == query.lower(),
    )
    stmt = (
        select(Ingredient.ingredient_id)
        .where(
            or_(
                Ingredient.name_kr.ilike(f"%{query}%"),
                Ingredient.name_en.ilike(f"%{query}%"),
                cast(Ingredient.synonyms, String).ilike(f'%"{query}"%'),
            )
        )
        .order_by(exact_match.desc(), Ingredient.name_kr)
    )
    ids = list(db.scalars(stmt).all())
    if ids:
        return ids

    return fuzzy_match.search(query)


@router.get("", response_model=list[IngredientDetail])
def list_ingredients(
    query: str | None = Query(default=None, description="name_kr/name_en/synonyms 검색어"),
    db: Session = Depends(get_db),
):
    if not query:
        ingredients = db.scalars(_detail_query().order_by(Ingredient.name_kr)).all()
        return [_to_detail(ingredient) for ingredient in ingredients]

    ids = search_ingredient_ids(query, db)
    if not ids:
        return []
    by_id = {
        ingredient.ingredient_id: ingredient
        for ingredient in db.scalars(_detail_query().where(Ingredient.ingredient_id.in_(ids))).all()
    }
    return [_to_detail(by_id[iid]) for iid in ids if iid in by_id]


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


@router.get("/{ingredient_id}/relations", response_model=list[IngredientRelationRead])
def get_ingredient_relations(ingredient_id: int, db: Session = Depends(get_db)):
    if db.get(Ingredient, ingredient_id) is None:
        raise HTTPException(status_code=404, detail="Ingredient not found")

    stmt = (
        select(IngredientRelation)
        .options(
            selectinload(IngredientRelation.ingredient_a),
            selectinload(IngredientRelation.ingredient_b),
        )
        .where(
            or_(
                IngredientRelation.ingredient_a_id == ingredient_id,
                IngredientRelation.ingredient_b_id == ingredient_id,
            )
        )
    )
    relations = db.scalars(stmt).all()
    return [
        IngredientRelationRead(
            relation_id=relation.relation_id,
            relation_type=relation.relation_type,
            user_message=relation.user_message,
            related_ingredient=(
                relation.ingredient_b
                if relation.ingredient_a_id == ingredient_id
                else relation.ingredient_a
            ),
        )
        for relation in relations
    ]


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
        pg_insert(IngredientPurpose)
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


@router.post("/{ingredient_id}/generate-summary", response_model=LLMSummaryRead)
def generate_summary(ingredient_id: int, db: Session = Depends(get_db)):
    ingredient = db.scalars(
        select(Ingredient)
        .options(
            selectinload(Ingredient.ingredient_purposes).selectinload(IngredientPurpose.purpose)
        )
        .where(Ingredient.ingredient_id == ingredient_id)
    ).first()
    if ingredient is None:
        raise HTTPException(status_code=404, detail="Ingredient not found")

    existing = db.get(LLMSummary, ingredient_id)
    if existing is not None and existing.summary_text:
        return existing

    purpose_names = [
        ip.purpose.purpose_name
        for ip in ingredient.ingredient_purposes
        if ip.purpose and ip.purpose.purpose_name
    ]
    descriptions = [
        ip.purpose.description
        for ip in ingredient.ingredient_purposes
        if ip.purpose and ip.purpose.description
    ]
    if not descriptions:
        raise HTTPException(
            status_code=422, detail="No purpose description available to summarize"
        )

    description_text = " ".join(descriptions)
    purpose_text = ", ".join(purpose_names)

    try:
        summary_text = rewrite_description(
            ingredient_name=ingredient.name_kr,
            description=description_text,
            purpose=purpose_text,
        )
    except (requests.exceptions.RequestException, ValueError):
        summary_text = description_text

    generated_at = datetime.now(timezone.utc)
    stmt = (
        pg_insert(LLMSummary)
        .values(
            ingredient_id=ingredient_id,
            summary_text=summary_text,
            summary_generated_at=generated_at,
        )
        .on_conflict_do_update(
            index_elements=["ingredient_id"],
            set_={"summary_text": summary_text, "summary_generated_at": generated_at},
        )
    )
    db.execute(stmt)
    db.commit()
    return db.get(LLMSummary, ingredient_id)
