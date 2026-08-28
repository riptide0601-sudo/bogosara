"""피부 타입별 제품 위험성분 탐지.

큰 흐름: 피부 타입 → 피부 고민 → 위험 성분 목록 → 실제 제품 성분 → 위험성분 매칭 → 경고 표시.

[2026-08-21 로직 전면 개편] 기존에는 성분마다 -3~+3 "적합도 점수"를 매겨서 평균 내는
방식이었으나, 이 접근을 완전히 버렸다. 이유:
  1) 점수 자체가 가짜 정밀도였음 — "위험한지 아닌지"는 문헌 근거가 있어도, -2점과
     -3점의 차이가 실제로 뭘 의미하는지는 근거가 없음.
  2) 유저는 "이 성분이 얼마나 위험한지 등급"보다 "위험 성분이 들어있는지 여부" 자체에
     관심이 있음 — 조금이라도 안 좋은 작용이 있으면 피하고 싶어함.
  3) 긍정적 점수(+1~+3, "이 성분이 이 피부타입에 좋음")는 유저 관심사가 아니라고 판단해
     완전히 제외함. ingredient_skin_score 테이블에는 이제 "위험 성분"만 남아있음
     (평가 결과 score < 0 이었던 행만 유지, 나머지는 삭제).

그래서 이 모듈이 하는 일은 매우 단순해졌다: 제품 성분 중 ingredient_skin_score에
등록된 위험 성분과 겹치는 게 있으면 그 목록을 그대로 보여주는 것. 점수 합산도,
정규화도 하지 않는다.

[2026-08-21 추가 메모] "위험 성분이 제품 전성분표에서 상위권(주요성분)에 있는지,
하위권(미량 추정)에 있는지"는 노출량과 직결되는 중요한 정보지만, 이건 실제 제품별
전성분 순서 데이터와 연동해야 하는 별도 로직이라 이 모듈 범위 밖이다. 추후
product_ingredient 테이블에 순서/농도 정보가 갖춰지면 별도 함수로 구현 예정.

주의: ingredient_skin_score의 값 중 평가 완료되지 않았던 성분(evidence_level='E',
"화장품 성분과학 컨센서스, 개별 문헌 미검증")은 검증을 이어가지 않기로 하고 삭제했다.
즉 지금 이 모듈이 참조하는 테이블에는 실제 논문/공식기관 자료로 뒷받침되는 위험
성분만 들어있다(evidence_level='B'). 다만 전체 화장품 성분 중 극히 일부(14개)만
검토된 상태이므로, "매칭되는 위험 성분이 없다"는 결과가 "검증된 안전"을 의미하지는
않는다 — 단지 "현재까지 확인된 위험 성분이 없다"는 뜻이다. 새로운 성분을 추가로
검증해 이 테이블에 넣는 작업은 계속 필요하다.

[2026-08-21 출처 검증 관련 메모] evidence_level='B'라고 해서 전부 같은 수준으로
검증된 건 아니다. 원문을 직접 열어 확인한 출처(EU SCCS, Nature Sci Rep 등)가 있는
반면, 검색엔진 스니펫만으로 인용한 출처도 아직 섞여있다(PubMed/PMC/Wiley 계열은
자동화 접속이 봇 차단에 걸려 직접 열람이 잘 안 됨). 실제로 이 검증 과정에서 두 건의
오류를 발견해 정정한 바 있다 — 에탄올 caution이 논문의 실제 결론(저농도는 안전)을
반영 못 하고 있었고, 캠퍼는 원래 인용한 논문이 자극 유발 근거가 아니라 오히려
치료 후보물질 임상시험이라 출처 자체가 안 맞았다. source 컬럼에 있는 링크를 사람이
직접 열어서 재확인하는 절차를 나머지 성분에도 적용하는 게 좋다.
"""

from collections import defaultdict
from dataclasses import dataclass, field

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.ingredient import Ingredient
from app.models.ingredient_skin_score import SKIN_TYPES, IngredientSkinScore
from app.models.product_ingredient import ProductIngredient


@dataclass
class RiskIngredient:
    ingredient_id: int
    name_kr: str | None
    risk_type: str | None  # 예: "향료(EU 지정 알레르겐)", "수렴/용제"
    reason: str | None  # caution 텍스트 — 왜 위험한지 사람이 읽을 수 있는 설명
    source: str | None  # 근거 논문/기관 자료 (제목 + URL)


@dataclass
class SkinRiskResult:
    skin_type: str
    has_risk: bool  # 위험 성분이 하나라도 매칭됐는지 — 화면에 경고 배지를 띄울지 여부
    risk_ingredients: list[RiskIngredient] = field(default_factory=list)
    total_ingredient_count: int = 0  # 제품 전성분 개수 (참고용)


def compute_skin_risk(product_id: str, skin_type: str, db: Session) -> SkinRiskResult:
    """제품 성분 중 해당 피부 타입에 위험한 것으로 등록된 성분을 찾아 반환한다.

    ingredient_skin_score 테이블엔 이제 "위험 성분"만 들어있으므로(평가 결과 마이너스였던
    것만 남김), 단순히 제품 성분 ID와 겹치는 행을 찾기만 하면 된다. 점수 합산·정규화 없음.
    """
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

    # skin_type == 조회한 피부타입인 행 + skin_type == '전체'(피부타입 무관 위험, 예: 향료
    # 알레르겐)인 행을 모두 가져온다. 향료류처럼 "피부가 건성이든 지성이든 상관없이
    # 개인 감작 여부로 생기는 위험"을 굳이 4개 피부타입 행으로 쪼개면 같은 내용이
    # 반복돼 보이므로, 그런 성분은 DB에 skin_type='전체' 한 줄로만 저장돼 있다.
    rows = db.execute(
        select(IngredientSkinScore).where(
            IngredientSkinScore.ingredient_id.in_(ingredient_ids),
            IngredientSkinScore.skin_type.in_([skin_type, "전체"]),
            IngredientSkinScore.is_risk.is_(True),
        )
    ).scalars().all()

    risk_ingredients = [
        RiskIngredient(
            ingredient_id=row.ingredient_id,
            name_kr=row.ingredient.name_kr if row.ingredient else None,
            risk_type=row.function,
            reason=row.caution,
            source=row.source,
        )
        for row in rows
    ]

    return SkinRiskResult(
        skin_type=skin_type,
        has_risk=len(risk_ingredients) > 0,
        risk_ingredients=risk_ingredients,
        total_ingredient_count=total_ingredient_count,
    )


def compute_all_skin_risks(product_id: str, db: Session) -> list[SkinRiskResult]:
    return [compute_skin_risk(product_id, skin_type, db) for skin_type in SKIN_TYPES]


# 문장에서 "전체"는 특정 피부타입이 아니라 향료 알레르겐처럼 피부타입 무관 항목이라
# SKIN_TYPES 뒤(마지막)에 오게 정렬하고, 표현도 "~에"가 아니라 "전체 피부타입"으로 바꾼다.
_SUMMARY_SKIN_TYPE_ORDER = {skin_type: i for i, skin_type in enumerate(SKIN_TYPES)}
_SUMMARY_SKIN_TYPE_ORDER["전체"] = len(SKIN_TYPES)
_SUMMARY_POLARITY_LABEL = {False: "좋은", True: "유의해야할"}


@dataclass
class SkinTypeCount:
    skin_type: str  # SKIN_TYPES 중 하나 또는 "전체"(피부타입 무관, 향료 알레르겐 등)
    good_count: int  # is_risk=False로 등록된 성분 개수(궁합 좋음)
    caution_count: int  # is_risk=True로 등록된 성분 개수(위험/유의)
    # 막대를 클릭했을 때 바로 보여줄 실제 성분명 목록 — good_count/caution_count와 같은
    # 근거(ingredient_skin_score)에서 뽑은, 실제로 이 제품 전성분에 들어있는 성분 이름.
    good_ingredients: list[str] = field(default_factory=list)
    caution_ingredients: list[str] = field(default_factory=list)


def compute_skin_type_counts(product_id: str, db: Session) -> list[SkinTypeCount]:
    """"피부 타입별 참고" 막대바용 — 피부타입마다 좋은/유의 성분이 몇 개(와 어떤 성분인지)를
    구조화된 형태로 반환한다(summarize_skin_score_matches의 문장 버전과 같은 근거, 형태만 다름).
    매칭이 하나도 없는 피부타입은 목록에서 아예 빠진다(0/0을 굳이 안 보여줌).
    "전체"(피부타입 무관, 향료 알레르겐 등)는 이 막대바에서는 제외한다 — 4개 피부타입별
    비교가 목적이라 "전체" 항목이 섞이면 오히려 헷갈린다는 피드백으로 뺐다.
    """
    rows = db.execute(
        select(
            IngredientSkinScore.skin_type,
            IngredientSkinScore.is_risk,
            ProductIngredient.ingredient_id,
            Ingredient.name_kr,
        )
        .join(
            ProductIngredient,
            ProductIngredient.ingredient_id == IngredientSkinScore.ingredient_id,
        )
        .join(Ingredient, Ingredient.ingredient_id == IngredientSkinScore.ingredient_id)
        .where(ProductIngredient.product_id == product_id)
        .distinct()
    ).all()

    # (skin_type, is_risk) -> {ingredient_id: name} — distinct()가 (skin_type, is_risk,
    # ingredient_id, name) 조합 기준이라, 같은 성분이 이 조합 안에서 두 번 잡히진 않는다.
    by_skin_type: dict[str, dict[bool, dict[int, str | None]]] = defaultdict(lambda: defaultdict(dict))
    for skin_type, is_risk, ingredient_id, name_kr in rows:
        by_skin_type[skin_type][is_risk][ingredient_id] = name_kr

    def names(ingredients: dict[int, str | None]) -> list[str]:
        return sorted(name for name in ingredients.values() if name)

    result = [
        SkinTypeCount(
            skin_type=skin_type,
            good_count=len(by_type.get(False, {})),
            caution_count=len(by_type.get(True, {})),
            good_ingredients=names(by_type.get(False, {})),
            caution_ingredients=names(by_type.get(True, {})),
        )
        for skin_type, by_type in by_skin_type.items()
        if skin_type != "전체"
    ]
    result.sort(key=lambda item: _SUMMARY_SKIN_TYPE_ORDER.get(item.skin_type, 99))
    return result


def summarize_skin_score_matches(product_ids: list[str], db: Session) -> dict[str, str]:
    """검색 결과 등 여러 제품을 한 번에 보여줄 때, 제품마다 ingredient_skin_score에
    매칭되는 성분이 있는지를 "지성에 좋은 성분 2개, 건성에 유의해야할 성분 1개
    있습니다." 같은 한 줄 요약으로 만든다. 매칭이 하나도 없으면 "..."을 반환한다.

    N개 제품을 한 쿼리로 집계해서(product_ingredient x ingredient_skin_score 조인 후
    product_id/skin_type/is_risk 별 개수) N+1 쿼리를 피한다.
    """
    if not product_ids:
        return {}

    rows = db.execute(
        select(
            ProductIngredient.product_id,
            IngredientSkinScore.skin_type,
            IngredientSkinScore.is_risk,
            func.count(func.distinct(ProductIngredient.ingredient_id)),
        )
        .join(
            IngredientSkinScore,
            IngredientSkinScore.ingredient_id == ProductIngredient.ingredient_id,
        )
        .where(ProductIngredient.product_id.in_(product_ids))
        .group_by(ProductIngredient.product_id, IngredientSkinScore.skin_type, IngredientSkinScore.is_risk)
    ).all()

    grouped: dict[str, list[tuple[str, bool, int]]] = defaultdict(list)
    for product_id, skin_type, is_risk, count in rows:
        grouped[product_id].append((skin_type, is_risk, count))

    summaries: dict[str, str] = {}
    for product_id in product_ids:
        items = grouped.get(product_id)
        if not items:
            summaries[product_id] = "..."
            continue

        items.sort(key=lambda item: (_SUMMARY_SKIN_TYPE_ORDER.get(item[0], 99), item[1]))
        parts = [
            f"{'전체 피부타입' if skin_type == '전체' else skin_type + '에'} "
            f"{_SUMMARY_POLARITY_LABEL[is_risk]} 성분 {count}개"
            for skin_type, is_risk, count in items
        ]
        summaries[product_id] = ", ".join(parts) + " 있습니다."

    return summaries
