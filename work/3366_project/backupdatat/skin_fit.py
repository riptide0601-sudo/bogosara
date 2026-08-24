"""피부 타입별 제품 적합도 계산.

큰 흐름: 피부 타입 → 피부 고민 → 필요한 성분 기능 → 실제 제품 성분 → 적합도 점수 → 추천.
이 모듈은 마지막 두 단계(제품 성분 → 적합도 점수)를 맡는다 — 제품에 들어있는 성분들을
ingredient_skin_score에서 찾아 해당 피부 타입 점수를 모두 더한 뒤, 0~100점으로 정규화한다.

주의: ingredient_skin_score의 시드 값은 피부과 가이드(AAD)·문헌에서 소개된 성분별
경향을 참고해 만든 "설계 단계 예시 점수"다. 실제 서비스에 쓰려면 성분별 근거를 개별
검토해서 점수를 다시 조정해야 한다 — 이 알고리즘은 그 점수를 제품 단위로 합산하는
계산 로직을 제공하는 것이지, 점수 자체의 의학적 정확성을 보장하지 않는다.
"""

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ingredient_skin_score import SKIN_TYPES, IngredientSkinScore
from app.models.product_ingredient import ProductIngredient

_MAX_ABS_SCORE = 3  # IngredientSkinScore.score의 범위(-3~+3) 중 절댓값 최대치.


@dataclass
class SkinScoreBreakdownItem:
    ingredient_id: int
    name_kr: str | None
    score: int
    function: str | None
    caution: str | None


@dataclass
class SkinFitResult:
    skin_type: str
    fit_score: float  # 0~100으로 정규화된 적합도 점수 (50 = 중립)
    raw_score: int  # 매칭된 성분들의 점수 합 (정규화 전)
    matched_count: int  # 점수 데이터가 있는 성분 개수
    total_ingredient_count: int  # 제품 전성분 개수 (매칭 여부 무관)
    breakdown: list[SkinScoreBreakdownItem] = field(default_factory=list)


def _normalize(raw_score: int, matched_count: int) -> float:
    """합산 점수를 0~100 스케일로 정규화한다 (50 = 중립, 매칭된 성분이 없으면 50).

    이론상 최댓값은 matched_count * 3, 최솟값은 -matched_count * 3이므로,
    그 구간에서의 위치를 0~100으로 선형 변환한다.
    """
    if matched_count == 0:
        return 50.0
    max_possible = _MAX_ABS_SCORE * matched_count
    normalized = 50 + (raw_score / max_possible) * 50
    return round(max(0.0, min(100.0, normalized)), 1)


def compute_skin_fit(product_id: str, skin_type: str, db: Session) -> SkinFitResult:
    if skin_type not in SKIN_TYPES:
        raise ValueError(f"알 수 없는 피부 타입입니다: {skin_type} (허용값: {SKIN_TYPES})")

    ingredient_ids = list(
        db.scalars(
            select(ProductIngredient.ingredient_id).where(
                ProductIngredient.product_id == product_id
            )
        )
    )
    total_ingredient_count = len(ingredient_ids)

    rows = db.execute(
        select(IngredientSkinScore).where(
            IngredientSkinScore.ingredient_id.in_(ingredient_ids),
            IngredientSkinScore.skin_type == skin_type,
        )
    ).scalars().all()

    breakdown = [
        SkinScoreBreakdownItem(
            ingredient_id=row.ingredient_id,
            name_kr=row.ingredient.name_kr if row.ingredient else None,
            score=row.score,
            function=row.function,
            caution=row.caution,
        )
        for row in rows
    ]
    breakdown.sort(key=lambda item: item.score, reverse=True)

    raw_score = sum(item.score for item in breakdown)
    matched_count = len(breakdown)

    return SkinFitResult(
        skin_type=skin_type,
        fit_score=_normalize(raw_score, matched_count),
        raw_score=raw_score,
        matched_count=matched_count,
        total_ingredient_count=total_ingredient_count,
        breakdown=breakdown,
    )


def compute_all_skin_fits(product_id: str, db: Session) -> list[SkinFitResult]:
    return [compute_skin_fit(product_id, skin_type, db) for skin_type in SKIN_TYPES]
