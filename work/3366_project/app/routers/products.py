import math
import re
from datetime import datetime, timezone

import requests
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db, upsert_insert
from app.llm_client import summarize_product
from app.marketing_families import compute_matched_families
from app.purpose_counts import compute_purpose_counts
from app.models.ingredient import Ingredient
from app.models.ingredient_family import IngredientFamily
from app.models.ingredient_family_member import IngredientFamilyMember
from app.models.ingredient_purpose import IngredientPurpose
from app.models.ingredient_relation import IngredientRelation
from app.models.product import Product
from app.models.product_family_member import ProductFamilyMember
from app.models.product_ingredient import ProductIngredient
from app.models.ingredient_skin_score import SKIN_TYPES
from app.product_category import ALL_CATEGORIES, classify as classify_category
from app.schemas.ingredient import IngredientDetail
from app.schemas.ingredient_family import FamilyRankRead
from app.schemas.ingredient_relation import IngredientRelationRead
from app.search_service import search_products
from app.schemas.product import (
    ProductCreate,
    ProductDetail,
    ProductIngredientDetail,
    ProductIngredientLink,
    ProductRead,
    ProductSimilarityRead,
)
from app.schemas.skin_fit import SkinRiskRead
from app.similarity import DEFAULT_TOP_K, find_similar_products
from app.skin_fit import (
    compute_all_skin_risks,
    compute_skin_risk,
    compute_skin_type_counts,
    summarize_skin_score_matches,
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


def _with_skin_score_summary(products: list[Product], db: Session) -> list[ProductRead]:
    """제품 목록에 ingredient_skin_score 매칭 요약 문장을 붙인다 (app/skin_fit.py
    summarize_skin_score_matches 참고). N개 제품을 한 쿼리로 집계해 N+1을 피한다."""
    summaries = summarize_skin_score_matches([p.product_id for p in products], db)
    result = []
    for p in products:
        item = ProductRead.model_validate(p)
        item.skin_score_summary = summaries.get(p.product_id, "...")
        result.append(item)
    return result


def _build_similar_products(
    product_id: str, db: Session, *, min_score: float, limit: int
) -> list[ProductSimilarityRead]:
    scored = find_similar_products(product_id, db, min_score=min_score, limit=limit)
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


def _relations_by_ingredient_id(
    ingredient_ids: list[int], db: Session
) -> dict[int, list[IngredientRelationRead]]:
    """제품 전성분 각각에 걸린 시너지/악화 관계를 한 번의 쿼리로 모아, ingredient_id별로 묶는다
    (성분 수만큼 반복 조회하는 N+1을 피하기 위함). 관계 상대 성분이 같은 제품 안에 있는지는
    따지지 않고, 이 성분에 걸린 관계를 전부 담는다 — GET /ingredients/{id}/relations와 같은 기준."""
    if not ingredient_ids:
        return {}

    stmt = select(IngredientRelation).options(
        selectinload(IngredientRelation.ingredient_a),
        selectinload(IngredientRelation.ingredient_b),
    ).where(
        or_(
            IngredientRelation.ingredient_a_id.in_(ingredient_ids),
            IngredientRelation.ingredient_b_id.in_(ingredient_ids),
        )
    )
    relations_by_id: dict[int, list[IngredientRelationRead]] = {iid: [] for iid in ingredient_ids}
    for relation in db.scalars(stmt).all():
        for this_id, other in (
            (relation.ingredient_a_id, relation.ingredient_b),
            (relation.ingredient_b_id, relation.ingredient_a),
        ):
            if this_id in relations_by_id:
                relations_by_id[this_id].append(
                    IngredientRelationRead(
                        relation_id=relation.relation_id,
                        relation_type=relation.relation_type,
                        user_message=relation.user_message,
                        related_ingredient=other,
                    )
                )
    return relations_by_id


def _to_detail(product: Product, db: Session) -> ProductDetail:
    detail = ProductDetail.model_validate(product)
    detail.ingredients = []
    sorted_pis = sorted(
        product.product_ingredients, key=lambda x: (x.label_rank is None, x.label_rank)
    )
    relations_by_id = _relations_by_ingredient_id([pi.ingredient_id for pi in sorted_pis], db)
    for pi in sorted_pis:
        ingredient_detail = IngredientDetail.model_validate(pi.ingredient)
        ingredient_detail.purposes = [ip.purpose for ip in pi.ingredient.ingredient_purposes]
        detail.ingredients.append(
            ProductIngredientDetail(
                label_rank=pi.label_rank,
                matched_text=pi.matched_text,
                ingredient=ingredient_detail,
                relations=relations_by_id.get(pi.ingredient_id, []),
            )
        )
    # label_rank 상위 DEFAULT_TOP_K개 그대로 슬라이스 — ingredients가 이미 label_rank순
    # 정렬이라 바로 자르면 된다. (유사도는 이제 이 기준이 아니라 product.key_ingredients를
    # 쓴다 — app/similarity.py 참고)
    detail.top_ingredients = detail.ingredients[:DEFAULT_TOP_K]
    # 60~70% 구간이 텅 비어있어 70%는 너무 빡빡했음 — 50% 이상으로 완화해 더 많이 노출한다.
    detail.similar_products = _build_similar_products(
        product.product_id, db, min_score=0.5, limit=10
    )
    detail.skin_score_summary = summarize_skin_score_matches([product.product_id], db).get(
        product.product_id, "..."
    )
    detail.ingredient_families = compute_matched_families(product, db)
    detail.purpose_counts = compute_purpose_counts(product, db)
    detail.skin_type_counts = compute_skin_type_counts(product.product_id, db)
    return detail


@router.get("", response_model=list[ProductRead])
def list_products(
    query: str | None = Query(default=None, description="product_name/brand/category 검색어"),
    category: str | None = Query(
        default=None,
        description="카테고리 필터: " + ", ".join(c.name for c in ALL_CATEGORIES),
    ),
    db: Session = Depends(get_db),
):
    if query:
        # app/search_service.py: 검색어를 토큰화해 이름/브랜드/카테고리 중 어디든
        # 전부 매칭되는 제품을 랭킹 점수순으로 반환한다 (성분/배합목적 검색 없음).
        results = search_products(query, db)
        if category:
            results = [r for r in results if r.category == category]
        if not results:
            return []
        products_by_id = {
            p.product_id: p
            for p in db.scalars(
                select(Product).where(
                    Product.product_id.in_([r.product_id for r in results])
                )
            ).all()
        }
        products = [
            products_by_id[r.product_id] for r in results if r.product_id in products_by_id
        ]
    else:
        stmt = select(Product)
        if category:
            stmt = stmt.where(Product.category == category)
        products = db.scalars(stmt.order_by(Product.product_name)).all()

    return _with_skin_score_summary(products, db)


@router.post("", response_model=ProductRead, status_code=201)
def create_product(payload: ProductCreate, db: Session = Depends(get_db)):
    product = Product(**payload.model_dump())
    product.category = classify_category(product.product_name).name
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
    min_score: float = Query(default=0.5, ge=0.0, le=1.0),
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """주요 성분(product.key_ingredients) 기준 유사도. app/similarity.py 참고 —
    label_rank 상위 N개가 아니라 core_ingredient_selector가 뽑은 핵심 성분으로 비교한다."""
    if db.get(Product, product_id) is None:
        raise HTTPException(status_code=404, detail="Product not found")

    return _build_similar_products(product_id, db, min_score=min_score, limit=limit)


@router.get("/{product_id}/skin-fit", response_model=list[SkinRiskRead])
def get_product_skin_fit(
    product_id: str,
    skin_type: str | None = Query(
        default=None, description="지성/복합성/건성/민감성 중 하나. 생략하면 4개 전부 반환"
    ),
    db: Session = Depends(get_db),
):
    """피부 타입별 위험 성분 탐지. app/skin_fit.py 참고 — 적합도 점수 합산 방식은 폐기했고,
    제품 성분 중 해당 피부타입에 위험하다고 등록된 성분이 있는지만 확인해 보여준다."""
    if db.get(Product, product_id) is None:
        raise HTTPException(status_code=404, detail="Product not found")

    if skin_type is not None:
        if skin_type not in SKIN_TYPES:
            raise HTTPException(
                status_code=422, detail=f"skin_type은 {SKIN_TYPES} 중 하나여야 합니다"
            )
        results = [compute_skin_risk(product_id, skin_type, db)]
    else:
        results = compute_all_skin_risks(product_id, db)

    return [SkinRiskRead.model_validate(r, from_attributes=True) for r in results]


# scripts/import_product_list.py가 원본 라벨 텍스트를 그대로 옮겨 담을 때, 성분명 뒤
# 괄호 안에 함량이 써있으면(예: "소듐하이알루로네이트(2,400ppm)") matched_text에 그대로
# 살아있다. 라벨에 따라 단위가 %/ppm/ppb로 제각각이라 하나로 환산하지 않고, 라벨에 적힌
# 그대로("2,400ppm") 보여준다 — 없으면(대부분의 성분) None.
_CONCENTRATION_RE = re.compile(r"\(([\d,]+\.?\d*\s*(?:%|ppm|ppb))\)\s*$")


def extract_concentration(matched_text: str | None) -> str | None:
    if not matched_text:
        return None
    m = _CONCENTRATION_RE.search(matched_text)
    return m.group(1).replace(" ", "") if m else None


_CONC_VALUE_RE = re.compile(r"^([\d,]+\.?\d*)(%|ppm|ppb)$")
# 평균 계산용 — 라벨마다 단위가 제각각이라(위 extract_concentration은 원문 그대로 보여주지만)
# 평균을 내려면 하나로 맞춰야 한다. 1% = 10,000ppm = 10,000,000ppb.
_PERCENT_PER_UNIT = {"%": 1.0, "ppm": 1 / 10_000, "ppb": 1 / 10_000_000}


def concentration_to_percent(concentration: str | None) -> float | None:
    if not concentration:
        return None
    m = _CONC_VALUE_RE.match(concentration)
    if not m:
        return None
    value = float(m.group(1).replace(",", ""))
    return value * _PERCENT_PER_UNIT[m.group(2)]


def _compute_family_rank(db: Session, family_id: int, product_id: str) -> FamilyRankRead:
    family = db.get(IngredientFamily, family_id)

    member_ids = db.scalars(
        select(IngredientFamilyMember.ingredient_id).where(
            IngredientFamilyMember.family_id == family_id
        )
    ).all()

    curated_product_ids = db.scalars(
        select(ProductFamilyMember.product_id).where(ProductFamilyMember.family_id == family_id)
    ).all()

    rep_rank_stmt = (
        select(ProductIngredient.product_id, func.min(ProductIngredient.label_rank).label("rep_rank"))
        .where(
            ProductIngredient.product_id.in_(curated_product_ids),
            ProductIngredient.ingredient_id.in_(member_ids),
            ProductIngredient.label_rank.isnot(None),
        )
        .group_by(ProductIngredient.product_id)
    )
    rows = db.execute(rep_rank_stmt).all()
    this_row = next((r for r in rows if r.product_id == product_id), None)
    if this_row is None:
        # 큐레이션은 돼있지만(product_family_member) 실제 전성분표에서 이 계열 성분을 하나도
        # 못 찾은 경우 — "없다"고 단정하지 않고 "비교 데이터가 없다"로 완곡하게 표현한다.
        # 원인이 (a) 정말 그 성분이 없거나 (b) scripts/import_product_list.py의 매칭 실패로
        # 누락됐거나 둘 다일 수 있어서, 확정적인 문구는 피한다.
        return FamilyRankRead(family_name=family.family_name, has_data=False)

    ranks = [r.rep_rank for r in rows]
    this_rank_value = this_row.rep_rank
    rank = sum(1 for r in ranks if r < this_rank_value) + 1
    total_count = len(ranks)
    average = sum(ranks) / total_count

    # 큐레이션된 모든 제품의 "대표 성분" matched_text를 한 번에 조회 — 이 제품의 대표 성분
    # 함량(위 extract_concentration, 라벨 원문 그대로)과, 계열 평균 함량(전부 %로 환산해서
    # 평균) 둘 다 여기서 뽑는다. 라벨에 함량이 없는 제품은 평균 계산에서 자연히 빠진다.
    detail_rows = db.execute(
        select(
            ProductIngredient.product_id,
            ProductIngredient.label_rank,
            ProductIngredient.matched_text,
        ).where(
            ProductIngredient.product_id.in_(curated_product_ids),
            ProductIngredient.ingredient_id.in_(member_ids),
            ProductIngredient.label_rank.isnot(None),
        )
    ).all()
    rep_rank_by_product = {r.product_id: r.rep_rank for r in rows}
    rep_matched_text_by_product: dict[str, str] = {}
    for d in detail_rows:
        if d.label_rank == rep_rank_by_product.get(d.product_id):
            rep_matched_text_by_product.setdefault(d.product_id, d.matched_text)

    this_concentration = extract_concentration(rep_matched_text_by_product.get(product_id))
    rep_ingredient_id = next(
        (
            row.ingredient_id
            for row in db.execute(
                select(ProductIngredient.ingredient_id).where(
                    ProductIngredient.product_id == product_id,
                    ProductIngredient.ingredient_id.in_(member_ids),
                    ProductIngredient.label_rank == this_rank_value,
                )
            )
        ),
        None,
    )
    rep_ingredient = db.get(Ingredient, rep_ingredient_id) if rep_ingredient_id else None
    rep_name = (rep_ingredient.name_kr or rep_ingredient.name_en or "") if rep_ingredient else ""

    concentration_percents = [
        pct
        for text in rep_matched_text_by_product.values()
        if (pct := concentration_to_percent(extract_concentration(text))) is not None
    ]
    average_concentration_percent = (
        round(sum(concentration_percents) / len(concentration_percents), 4)
        if concentration_percents
        else None
    )

    return FamilyRankRead(
        family_name=family.family_name,
        representative_ingredient=rep_name,
        representative_concentration=this_concentration,
        label_rank=this_rank_value,
        rank=rank,
        total_count=total_count,
        average_label_rank=round(average, 1),
        top_percentile=math.ceil(rank / total_count * 100),
        average_concentration_percent=average_concentration_percent,
        concentration_sample_count=len(concentration_percents),
    )


@router.get("/{product_id}/family-rank", response_model=list[FamilyRankRead])
def get_product_family_rank(product_id: str, db: Session = Depends(get_db)):
    """제품 설명 화면의 "비슷한 제품과 비교하면" — 이 제품이 사람이 직접 큐레이션한 성분 계열
    비교 대상(scripts/backfill_product_family.py로 채운 product_family_member)에 속해 있으면,
    같은 계열의 다른 큐레이션 제품들과 label_rank(전성분표 순위) 기준으로 비교한다.

    비교 모수를 ingredient_family_member(성분명 키워드 매칭)만으로 잡으면 그 계열 성분이
    조금이라도 들어간 DB 전체 제품까지 다 섞여 순위가 무의미해지므로, 실제 비교는
    product_family_member에 등록된 제품끼리만 한다. ingredient_family_member는 그 안에서
    "어떤 성분이 대표 성분인지"를 찾는 데만 쓴다.

    한 제품이 여러 계열에 동시에 큐레이션될 수 있어(예: 더마토리 히알샷은 히알루론산 계열이자
    B5 계열) 리스트로 응답한다 — 어떤 계열에도 속하지 않으면 빈 리스트(에러 아님, 프론트는
    이 경우 섹션 자체를 숨긴다)."""
    if db.get(Product, product_id) is None:
        raise HTTPException(status_code=404, detail="Product not found")

    family_ids = db.scalars(
        select(ProductFamilyMember.family_id).where(ProductFamilyMember.product_id == product_id)
    ).all()

    return [_compute_family_rank(db, family_id, product_id) for family_id in family_ids]


@router.put("/{product_id}/ingredients", status_code=204)
def link_ingredient(
    product_id: str, payload: ProductIngredientLink, db: Session = Depends(get_db)
):
    if db.get(Product, product_id) is None:
        raise HTTPException(status_code=404, detail="Product not found")
    if db.get(Ingredient, payload.ingredient_id) is None:
        raise HTTPException(status_code=404, detail="Ingredient not found")

    stmt = (
        upsert_insert(ProductIngredient)
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
