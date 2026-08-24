"""제품 간 유사도: 주요 성분과 나머지 성분을 나눠서 각각 자카드 유사도를 구한 뒤 7:3으로 합산합니다.

[2026-08-24 개편] "주요 성분"은 더 이상 label_rank(전성분표 배합 순서) 상위 N개가 아니라
product.key_ingredients(app/core_ingredient_selector.py가 정제수·용제·계면활성제 등을
걸러내고 화학적으로 비슷한 성분끼리 묶어서 뽑은 결과, scripts/backfill_key_ingredients.py로
채움)다. 배합 순서만으로는 정제수 다음 성분이 우연히 주요 성분 취급되는 등 노이즈가 있었는데,
core_ingredient_selector의 필터링을 재사용해 더 의미 있는 "핵심 성분"으로 유사도를 낸다.
key_ingredients가 아직 비어있는 제품(백필 전)은 전체 성분이 전부 "나머지 성분"으로만 잡힌다.

주요 성분이 겹치는 제품일수록 핵심 활성 성분이 비슷하다고 보고 더 큰 가중치를 주고,
나머지(베이스·보조) 성분이 겹치는 정도는 30%만 반영합니다.
"""

import json
from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ingredient import Ingredient
from app.models.product import Product
from app.models.product_ingredient import ProductIngredient

KEY_INGREDIENT_WEIGHT = 0.7
REST_INGREDIENT_WEIGHT = 0.3

# product.key_ingredients가 core_ingredient_selector 기준 최대 5개라, 제품 상세의
# top_ingredients(label_rank 기준 상위 N개, app/routers/products.py 참고) 표시 개수도
# 같은 값을 맞춰 쓴다 — 유사도의 "주요 성분" 정의와는 이제 별개다.
DEFAULT_TOP_K = 5


@dataclass(frozen=True)
class ProductIngredientSets:
    key_ids: frozenset[int]
    rest_ids: frozenset[int]


def _jaccard(a: frozenset[int], b: frozenset[int]) -> float:
    if not a and not b:
        return 0.0
    return len(a & b) / len(a | b)


def similarity_score(a: ProductIngredientSets, b: ProductIngredientSets) -> float:
    key_similarity = _jaccard(a.key_ids, b.key_ids)
    rest_similarity = _jaccard(a.rest_ids, b.rest_ids)
    return KEY_INGREDIENT_WEIGHT * key_similarity + REST_INGREDIENT_WEIGHT * rest_similarity


def _all_ingredient_sets(db: Session) -> dict[str, ProductIngredientSets]:
    rows = db.execute(
        select(ProductIngredient.product_id, ProductIngredient.ingredient_id, Ingredient.name_kr).join(
            Ingredient, Ingredient.ingredient_id == ProductIngredient.ingredient_id
        )
    ).all()

    all_ids: dict[str, set[int]] = defaultdict(set)
    id_by_name: dict[str, dict[str, int]] = defaultdict(dict)
    for product_id, ingredient_id, name_kr in rows:
        all_ids[product_id].add(ingredient_id)
        if name_kr:
            id_by_name[product_id][name_kr] = ingredient_id

    key_ingredients_json = dict(
        db.execute(select(Product.product_id, Product.key_ingredients)).all()
    )

    result = {}
    for product_id, ids in all_ids.items():
        raw = key_ingredients_json.get(product_id)
        key_names = json.loads(raw) if raw else []
        names_to_ids = id_by_name[product_id]
        key_ids = frozenset(
            names_to_ids[name] for name in key_names if name in names_to_ids
        )
        result[product_id] = ProductIngredientSets(
            key_ids=key_ids,
            rest_ids=frozenset(ids - key_ids),
        )
    return result


def find_similar_products(
    product_id: str,
    db: Session,
    min_score: float = 0.5,
    limit: int = 10,
) -> list[tuple[str, float]]:
    """product_id와 유사한 제품을 (product_id, score) 목록으로, 점수 내림차순 반환합니다.

    min_score 미만인 제품은 결과에서 제외합니다.
    """
    all_sets = _all_ingredient_sets(db)
    target = all_sets.get(product_id)
    if target is None:
        return []

    scored = [
        (other_id, similarity_score(target, other_sets))
        for other_id, other_sets in all_sets.items()
        if other_id != product_id
    ]
    scored = [pair for pair in scored if pair[1] >= min_score]
    scored.sort(key=lambda pair: pair[1], reverse=True)
    return scored[:limit]
