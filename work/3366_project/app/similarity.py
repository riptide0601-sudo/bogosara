"""제품 간 유사도: 세 가지 신호를 가중 합산합니다.

  1) 주요 성분(key_ingredients) 자카드 유사도 — 50%
  2) 나머지 성분 자카드 유사도 — 20%
  3) 배합목적 TF-IDF 벡터 코사인 유사도 — 30%

[2026-08-24 개편] "주요 성분"은 더 이상 label_rank(전성분표 배합 순서) 상위 N개가 아니라
product.key_ingredients(app/core_ingredient_selector.py가 정제수·용제·계면활성제 등을
걸러내고 화학적으로 비슷한 성분끼리 묶어서 뽑은 결과, scripts/backfill_key_ingredients.py로
채움)다. key_ingredients가 아직 비어있는 제품(백필 전)은 전체 성분이 전부 "나머지 성분"으로만 잡힌다.

[2026-08-24 추가] 성분 ID가 하나도 안 겹쳐도 "하는 일"이 비슷한 제품이 있다 — 예를 들어
비타민C 유도체가 서로 다른 두 제품은 성분표에 겹치는 이름이 없어도 둘 다 "미백/항산화"
성분 위주다. 이걸 잡기 위해 제품마다 배합목적(purpose) 분포를 TF-IDF 벡터로 만들고
코사인 유사도를 추가했다. TF-IDF를 쓰는 이유: "피부컨디셔닝제(기타)"처럼 8천 건 넘게
등장하는 흔한 목적은 변별력이 없어 낮게, "미백"·"자외선차단"처럼 일부 제품에만 등장하는
목적은 그 제품의 정체성을 잘 드러내므로 높게 가중하기 위함(app/routers 쪽의
LOW_INFO_PURPOSES 취급과 같은 문제의식).
"""

import json
import math
from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ingredient import Ingredient
from app.models.ingredient_purpose import IngredientPurpose
from app.models.product import Product
from app.models.product_ingredient import ProductIngredient

KEY_INGREDIENT_WEIGHT = 0.5
REST_INGREDIENT_WEIGHT = 0.2
PURPOSE_VECTOR_WEIGHT = 0.3

# product.key_ingredients가 core_ingredient_selector 기준 최대 5개라, 제품 상세의
# top_ingredients(label_rank 기준 상위 N개, app/routers/products.py 참고) 표시 개수도
# 같은 값을 맞춰 쓴다 — 유사도의 "주요 성분" 정의와는 이제 별개다.
DEFAULT_TOP_K = 5

PurposeVector = dict[int, float]


@dataclass(frozen=True)
class ProductIngredientSets:
    key_ids: frozenset[int]
    rest_ids: frozenset[int]
    purpose_vector: PurposeVector


def _jaccard(a: frozenset[int], b: frozenset[int]) -> float:
    if not a and not b:
        return 0.0
    return len(a & b) / len(a | b)


def cosine_similarity(a: PurposeVector, b: PurposeVector) -> float:
    """희소 벡터(딕셔너리) 코사인 유사도. 공통 키가 없으면 0."""
    if not a or not b:
        return 0.0
    shared_keys = a.keys() & b.keys()
    if not shared_keys:
        return 0.0
    dot = sum(a[k] * b[k] for k in shared_keys)
    norm_a = math.sqrt(sum(v * v for v in a.values()))
    norm_b = math.sqrt(sum(v * v for v in b.values()))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def similarity_score(a: ProductIngredientSets, b: ProductIngredientSets) -> float:
    key_similarity = _jaccard(a.key_ids, b.key_ids)
    rest_similarity = _jaccard(a.rest_ids, b.rest_ids)
    purpose_similarity = cosine_similarity(a.purpose_vector, b.purpose_vector)
    return (
        KEY_INGREDIENT_WEIGHT * key_similarity
        + REST_INGREDIENT_WEIGHT * rest_similarity
        + PURPOSE_VECTOR_WEIGHT * purpose_similarity
    )


def _purpose_term_frequencies(db: Session) -> dict[str, dict[int, int]]:
    """제품별 {purpose_id: 그 배합목적을 가진 성분 개수}. TF-IDF의 TF(term frequency)."""
    rows = db.execute(
        select(ProductIngredient.product_id, IngredientPurpose.purpose_id).join(
            IngredientPurpose, IngredientPurpose.ingredient_id == ProductIngredient.ingredient_id
        )
    ).all()

    tf: dict[str, dict[int, int]] = defaultdict(lambda: defaultdict(int))
    for product_id, purpose_id in rows:
        tf[product_id][purpose_id] += 1
    return tf


def _idf_weights(tf: dict[str, dict[int, int]]) -> dict[int, float]:
    """배합목적별 역문서빈도(IDF). 거의 모든 제품에 등장하는 흔한 목적은 낮게,
    일부 제품에만 등장하는 특징적인 목적은 높게 가중해서 변별력을 준다."""
    n_products = len(tf)
    doc_freq: dict[int, int] = defaultdict(int)
    for purposes in tf.values():
        for purpose_id in purposes:
            doc_freq[purpose_id] += 1
    # +1 스무딩: 극단적으로 흔하거나 희귀한 목적이 idf를 0이나 무한대로 보내지 않게 한다.
    return {
        purpose_id: math.log((n_products + 1) / (df + 1)) + 1
        for purpose_id, df in doc_freq.items()
    }


def _all_purpose_vectors(db: Session) -> dict[str, PurposeVector]:
    tf = _purpose_term_frequencies(db)
    idf = _idf_weights(tf)
    return {
        product_id: {purpose_id: count * idf[purpose_id] for purpose_id, count in purposes.items()}
        for product_id, purposes in tf.items()
    }


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
    purpose_vectors = _all_purpose_vectors(db)

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
            purpose_vector=purpose_vectors.get(product_id, {}),
        )
    return result


# 특정 제품에 대해 알고리즘 계산 결과 대신 고정으로 보여줄 추천 목록(사람이 직접 정함).
# 전체 유사도 공식(위 similarity_score)은 그대로 두고, 이 제품만 예외로 지정한 순서 그대로
# 보여준다 — 더마토리 히알샷 클릭 시 "이런 제품은 어때요?"에 히알루론산 계열 제품 3개
# (토리든/메디필/닥터지)가 뜨게 해달라는 요청으로 추가. 오어스가 원래 2순위였지만 사진이
# 없어서 제외 — 그 다음 후보였던 성분에디터는 사진은 있지만 이름에 "히알"이 없는(성분표
# 기준으로만 큐레이션된) 제품이라 다시 제외하고, 사진 있고 이름에도 "히알"이 들어간
# 히알루론산 제품 중 점수가 가장 높은 메디필로 교체.
MANUAL_SIMILAR_OVERRIDES: dict[str, list[str]] = {
    "p-cb5c0bb61e60": ["p-d70a49bcc485", "p-00c65b3d85b6", "p-8d07a757af76"],
}


def _purpose_vector_for_ingredients(
    ingredient_ids: set[int], idf: dict[int, float], db: Session
) -> PurposeVector:
    rows = db.execute(
        select(IngredientPurpose.purpose_id).where(
            IngredientPurpose.ingredient_id.in_(ingredient_ids)
        )
    ).all()
    tf: dict[int, int] = defaultdict(int)
    for (purpose_id,) in rows:
        tf[purpose_id] += 1
    return {purpose_id: count * idf.get(purpose_id, 0.0) for purpose_id, count in tf.items()}


def find_similar_products_for_ingredients(
    ingredient_ids: list[int],
    key_ingredient_ids: list[int],
    db: Session,
    min_score: float = 0.5,
    limit: int = 10,
) -> list[tuple[str, float]]:
    """find_similar_products()의 스캔용 버전 — 등록된 product_id가 없는 임시(ad-hoc) 성분
    집합(OCR로 매칭된 성분들)을 대상으로 같은 similarity_score()/전체 제품 집합을 써서 유사
    제품을 찾는다. key_ingredient_ids는 ingredient_ids의 부분집합이어야 한다(app/ocr_summary.py
    get_key_ingredients가 뽑은 이름을 ingredient_id로 변환한 것, app/routers/ocr.py 참고)."""
    all_sets = _all_ingredient_sets(db)
    tf = _purpose_term_frequencies(db)
    idf = _idf_weights(tf)

    all_ids = set(ingredient_ids)
    key_ids = frozenset(i for i in key_ingredient_ids if i in all_ids)
    target = ProductIngredientSets(
        key_ids=key_ids,
        rest_ids=frozenset(all_ids - key_ids),
        purpose_vector=_purpose_vector_for_ingredients(all_ids, idf, db),
    )

    scored = [(other_id, similarity_score(target, other_sets)) for other_id, other_sets in all_sets.items()]
    scored = [pair for pair in scored if pair[1] >= min_score]
    scored.sort(key=lambda pair: pair[1], reverse=True)
    return scored[:limit]


def find_similar_products(
    product_id: str,
    db: Session,
    min_score: float = 0.5,
    limit: int = 10,
) -> list[tuple[str, float]]:
    """product_id와 유사한 제품을 (product_id, score) 목록으로, 점수 내림차순 반환합니다.

    min_score 미만인 제품은 결과에서 제외합니다. MANUAL_SIMILAR_OVERRIDES에 등록된
    product_id는 알고리즘 대신 그 목록을 지정한 순서 그대로 반환한다(점수는 표시에는
    안 쓰이지만 참고용으로 실제 유사도를 계산해 채운다).
    """
    all_sets = _all_ingredient_sets(db)
    target = all_sets.get(product_id)
    if target is None:
        return []

    override = MANUAL_SIMILAR_OVERRIDES.get(product_id)
    if override:
        return [
            (other_id, similarity_score(target, all_sets[other_id]))
            for other_id in override
            if other_id in all_sets
        ][:limit]

    scored = [
        (other_id, similarity_score(target, other_sets))
        for other_id, other_sets in all_sets.items()
        if other_id != product_id
    ]
    scored = [pair for pair in scored if pair[1] >= min_score]
    scored.sort(key=lambda pair: pair[1], reverse=True)
    return scored[:limit]
