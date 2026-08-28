"""마이페이지 "내 화장품 조합" 분석 — 유저가 실제 쓰는 제품 여러 개를 하나의 루틴으로
묶어, 전성분을 합쳐서 조합 전체를 판단한다. app/skin_fit.py(제품 하나 기준)와 다르게
이 모듈은 여러 제품의 전성분 합집합을 대상으로 한다.

큰 흐름: 루틴 제품들 → 전성분 합집합(중복 성분 제거) → 배합목적(purpose)으로
수분/보습 밸런스 판정 + ingredient_skin_score로 유저 피부타입 기준 위험/궁합 성분 확인
→ 구조화된 결과 반환(문장 조립은 일부만 여기서, 나머지는 프론트가 리스트를 그대로 보여줌).

[2026-08-25] 여드름 유발 성분(코메도제닉) 판정은 이번 버전에서 뺐다 — DB에 아직
그 근거 데이터가 없다(ingredient_skin_score는 현재 향료 알레르겐 등 위주). 나중에
그 데이터가 추가되면 아래 스킨타입 위험/궁합 조회와 같은 패턴으로 붙이면 된다.

수분/보습 판정은 LLM이 아니라 배합목적(purpose) 카테고리 기반 규칙이다 — 실제
스킨케어에서 "수분(휴멕턴트) vs 보습·유수분막(옥클루시브/에몰리언트)"은 따로 논의되는
개념이라, 이 둘을 구분해야 "수분은 있는데 못 가두고 있다" 같은 판정이 가능하다. DB의
KCIA 배합목적 이름을 그대로 기준으로 삼았다(새 분류 체계를 만들지 않음).
"""

import json
from collections import Counter, defaultdict
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ingredient import Ingredient
from app.models.ingredient_purpose import IngredientPurpose
from app.models.ingredient_relation import IngredientRelation
from app.models.ingredient_skin_score import IngredientSkinScore
from app.models.product import Product
from app.models.product_ingredient import ProductIngredient
from app.models.purpose import Purpose
from app.product_category import get_info as get_category_info

HYDRATION_PURPOSES = {"보습", "보습제", "피부보습제", "피부컨디셔닝제(보습제)"}
OCCLUSION_PURPOSES = {
    "수분증발차단제",
    "피부컨디셔닝제(수분차단제)",
    "유연제",
    "피부유연화제",
    "피부컨디셔닝제(유연제)",
    "컨디셔닝제(유연제)",
    "피부보호제(유연제)",
}


@dataclass
class RoutineIngredientNote:
    ingredient_id: int
    name_kr: str | None
    description: str | None  # ingredient.summary — 성분 자체에 대한 일반 설명
    risk_type: str | None  # ingredient_skin_score.function
    reason: str | None  # ingredient_skin_score.caution — 이 피부타입에 왜 위험/궁합인지


@dataclass
class RoutineSkinTypeNote:
    skin_type: str
    risk_ingredients: list[RoutineIngredientNote] = field(default_factory=list)
    good_ingredients: list[RoutineIngredientNote] = field(default_factory=list)


@dataclass
class RoutineRelationNote:
    relation_type: str  # "시너지" | "악화"
    ingredient_a: str
    ingredient_b: str
    message: str | None  # ingredient_relation.user_message


@dataclass
class RoutineAnalysis:
    product_count: int
    ingredient_count: int
    headline: str
    overall_description: str
    hydration_note: str
    # 수분(휴멕턴트)/보습(옥클루시브·에몰리언트) 각각에 해당하는 배합목적을 가진 성분 개수 —
    # 프론트가 막대바(수분 N / 보습 N)로 시각화한다(SkinTypeCountBars와 같은 표현 방식).
    hydration_count: int
    occlusion_count: int
    skin_type_notes: list[RoutineSkinTypeNote]
    relations: list[RoutineRelationNote] = field(default_factory=list)
    hydration_ingredients: list[str] = field(default_factory=list)
    occlusion_ingredients: list[str] = field(default_factory=list)


def parse_json_list(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return []


def build_item_description(product: Product) -> str:
    """루틴에 등록한 제품 한 건에 대한 간단 설명 — app/routers/users.py가
    RoutineItemRead.description을 만들 때 쓴다. LLM 요약(product.summary)이 아직 없는
    제품(대부분)은 빈 문자열이다 — 핵심 성분은 이 문장이 아니라 RoutineItemRead.
    key_ingredients에 리스트로 따로 내려준다(프론트가 칩으로 보여줌)."""
    return product.summary or ""


def _build_headline(products: list[Product], ingredient_count: int) -> str:
    if not products:
        return "아직 등록한 화장품이 없어요."

    counts: dict[str, int] = defaultdict(int)
    for p in products:
        counts[get_category_info(p.category).name] += 1
    ordered = sorted(counts.items(), key=lambda kv: -kv[1])
    composition = " · ".join(f"{label} {count}개" for label, count in ordered)
    return f"{composition} — 총 {len(products)}개 제품, {ingredient_count}가지 성분으로 구성된 루틴이에요."


def _build_overall_description(products: list[Product]) -> str:
    """루틴 전체에 대한 한 단락 설명 — 제품마다 이미 계산돼 있는 key_purposes
    (core_ingredient_selector, scripts/backfill_key_ingredients.py)를 모아 가장 많이
    겹치는 효능 위주로 문장을 만든다. LLM 아님 — 기존 데이터 재활용."""
    if not products:
        return ""

    counter: Counter[str] = Counter()
    for p in products:
        counter.update(set(parse_json_list(p.key_purposes)))

    if not counter:
        return "선택하신 제품들의 핵심 효능 정보가 아직 없어요."

    top = [name for name, _ in counter.most_common(4)]
    return f"선택하신 {len(products)}개 제품은 {' · '.join(top)} 효과를 내는 성분 위주로 구성되어 있어요."


def _build_hydration_note(hydration_present: bool, occlusion_present: bool) -> str:
    if hydration_present and occlusion_present:
        return "수분과 보습이 모두 충분합니다."
    if hydration_present and not occlusion_present:
        return "수분은 충분하나 보습이 살짝 부족하여 보습 화장품을 추가하시면 좋습니다."
    if not hydration_present and occlusion_present:
        return "채워둔 수분을 붙잡아 줄 보습 성분은 있지만, 수분 자체를 공급하는 성분은 부족해요. 수분 성분이 있는 제품을 추가하시면 좋습니다."
    return "수분과 보습 성분이 모두 부족해 보여요. 수분·보습 제품을 추가하는 걸 추천해요."


def analyze_routine(product_ids: list[str], skin_types: list[str], db: Session) -> RoutineAnalysis:
    """루틴(product_ids)의 전성분을 합쳐서 수분/보습 밸런스와, 유저 skin_types 기준
    위험/궁합 성분을 판정한다. skin_types가 비어 있으면 skin_type_notes는 빈 리스트다
    (마이페이지에서 피부 타입을 아직 등록하지 않은 경우)."""
    if not product_ids:
        return RoutineAnalysis(
            product_count=0,
            ingredient_count=0,
            headline=_build_headline([], 0),
            overall_description="",
            hydration_note="화장품을 추가하면 여기서 조합을 분석해드려요.",
            hydration_count=0,
            occlusion_count=0,
            skin_type_notes=[],
        )

    products = list(db.scalars(select(Product).where(Product.product_id.in_(product_ids))).all())

    ingredient_rows = db.execute(
        select(ProductIngredient.product_id, ProductIngredient.ingredient_id, Ingredient.name_kr)
        .join(Ingredient, Ingredient.ingredient_id == ProductIngredient.ingredient_id)
        .where(ProductIngredient.product_id.in_(product_ids))
    ).all()
    # 성분 하나가 루틴 안에서 어느 제품(들)에 들어있는지 — ingredient_relation 매칭에서
    # "완전히 같은 제품 안에서만 같이 있는 조합"(그 제품 자체의 배합이라 새로운 정보가
    # 아님)을 걸러내는 데 쓴다. ingredient_ids는 여기서 중복 없이 뽑는다.
    products_by_ingredient: dict[int, set[str]] = defaultdict(set)
    name_by_ingredient: dict[int, str] = {}
    for product_id, ingredient_id, name_kr in ingredient_rows:
        products_by_ingredient[ingredient_id].add(product_id)
        if name_kr:
            name_by_ingredient[ingredient_id] = name_kr
    ingredient_ids = list(products_by_ingredient.keys())

    purpose_rows = db.execute(
        select(IngredientPurpose.ingredient_id, Purpose.purpose_name)
        .join(Purpose, Purpose.purpose_id == IngredientPurpose.purpose_id)
        .where(IngredientPurpose.ingredient_id.in_(ingredient_ids))
    ).all()
    purposes_by_ingredient: dict[int, set[str]] = defaultdict(set)
    for ingredient_id, purpose_name in purpose_rows:
        purposes_by_ingredient[ingredient_id].add(purpose_name)

    hydration_ingredients = [
        name_by_ingredient[iid]
        for iid in ingredient_ids
        if purposes_by_ingredient[iid] & HYDRATION_PURPOSES and iid in name_by_ingredient
    ]
    occlusion_ingredients = [
        name_by_ingredient[iid]
        for iid in ingredient_ids
        if purposes_by_ingredient[iid] & OCCLUSION_PURPOSES and iid in name_by_ingredient
    ]
    hydration_count = len(hydration_ingredients)
    occlusion_count = len(occlusion_ingredients)
    hydration_present = hydration_count > 0
    occlusion_present = occlusion_count > 0

    # 성분 간 시너지/악화 조합 — 루틴에 있는 성분끼리(양쪽 다 ingredient_ids 안에 있는
    # 경우) ingredient_relation에 등록된 관계가 있는지 확인한다. products_by_ingredient의
    # 합집합이 제품 1개뿐이면 "그 제품 안에서만 같이 있는 조합"이라 이미 그 제품 배합
    # 자체이지 여러 제품을 합쳐서 생긴 새로운 정보가 아니므로 건너뛴다.
    relations: list[RoutineRelationNote] = []
    if len(ingredient_ids) >= 2:
        relation_rows = db.execute(
            select(IngredientRelation).where(
                IngredientRelation.ingredient_a_id.in_(ingredient_ids),
                IngredientRelation.ingredient_b_id.in_(ingredient_ids),
            )
        ).scalars().all()
        for rel in relation_rows:
            union_products = products_by_ingredient[rel.ingredient_a_id] | products_by_ingredient[rel.ingredient_b_id]
            if len(union_products) < 2:
                continue
            relations.append(
                RoutineRelationNote(
                    relation_type=rel.relation_type,
                    ingredient_a=rel.ingredient_a.name_kr or "",
                    ingredient_b=rel.ingredient_b.name_kr or "",
                    message=rel.user_message,
                )
            )

    skin_type_notes: list[RoutineSkinTypeNote] = []
    if skin_types and ingredient_ids:
        score_rows = db.execute(
            select(IngredientSkinScore)
            .where(
                IngredientSkinScore.ingredient_id.in_(ingredient_ids),
                IngredientSkinScore.skin_type.in_([*skin_types, "전체"]),
            )
        ).scalars().all()

        by_skin_type: dict[str, list[IngredientSkinScore]] = defaultdict(list)
        for row in score_rows:
            # "전체"(피부타입 무관 위험, 예: 향료 알레르겐)는 유저가 고른 모든 피부타입에 같이 붙인다.
            targets = skin_types if row.skin_type == "전체" else [row.skin_type]
            for target in targets:
                by_skin_type[target].append(row)

        for skin_type in skin_types:
            rows = by_skin_type.get(skin_type, [])
            note = RoutineSkinTypeNote(skin_type=skin_type)
            for row in rows:
                item = RoutineIngredientNote(
                    ingredient_id=row.ingredient_id,
                    name_kr=row.ingredient.name_kr if row.ingredient else None,
                    description=row.ingredient.summary if row.ingredient else None,
                    risk_type=row.function,
                    reason=row.caution,
                )
                (note.risk_ingredients if row.is_risk else note.good_ingredients).append(item)
            skin_type_notes.append(note)

    return RoutineAnalysis(
        product_count=len(products),
        ingredient_count=len(ingredient_ids),
        headline=_build_headline(products, len(ingredient_ids)),
        overall_description=_build_overall_description(products),
        hydration_note=_build_hydration_note(hydration_present, occlusion_present),
        hydration_count=hydration_count,
        occlusion_count=occlusion_count,
        hydration_ingredients=hydration_ingredients,
        occlusion_ingredients=occlusion_ingredients,
        skin_type_notes=skin_type_notes,
        relations=relations,
    )
