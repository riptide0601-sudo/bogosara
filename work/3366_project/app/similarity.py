"""제품 간 유사도: 주요 성분과 나머지 성분을 나눠서 각각 자카드 유사도를 구한 뒤 7:3으로 합산합니다.

label_rank(전성분표 배합 순서)가 앞쪽인 상위 top_k개를 "주요 성분", 그 뒤를 "나머지 성분"으로
나눕니다. 주요 성분이 겹치는 제품일수록 핵심 활성 성분이 비슷하다고 보고 더 큰 가중치를 주고,
나머지(베이스·보조) 성분이 겹치는 정도는 30%만 반영합니다.
"""

from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.product_ingredient import ProductIngredient

KEY_INGREDIENT_WEIGHT = 0.7
REST_INGREDIENT_WEIGHT = 0.3

# label_rank(전성분표 배합 순서) 상위 몇 개까지를 "주요 성분"으로 볼지. 유사도 계산과
# 제품 상세의 key_ingredients 속성이 이 기준을 공유해야 서로 다른 정의로 어긋나지 않는다.
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


def _all_ingredient_sets(db: Session, top_k: int) -> dict[str, ProductIngredientSets]:
    rows = db.execute(
        select(ProductIngredient.product_id, ProductIngredient.ingredient_id)
        .order_by(ProductIngredient.product_id, ProductIngredient.label_rank)
    ).all()

    ordered_ids: dict[str, list[int]] = defaultdict(list)
    for product_id, ingredient_id in rows:
        ordered_ids[product_id].append(ingredient_id)

    return {
        product_id: ProductIngredientSets(
            key_ids=frozenset(ids[:top_k]),
            rest_ids=frozenset(ids[top_k:]),
        )
        for product_id, ids in ordered_ids.items()
    }


def find_similar_products(
    product_id: str,
    db: Session,
    top_k: int = DEFAULT_TOP_K,
    min_score: float = 0.5,
    limit: int = 10,
) -> list[tuple[str, float]]:
    """product_id와 유사한 제품을 (product_id, score) 목록으로, 점수 내림차순 반환합니다.

    min_score 미만인 제품은 결과에서 제외합니다.
    """
    all_sets = _all_ingredient_sets(db, top_k)
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
