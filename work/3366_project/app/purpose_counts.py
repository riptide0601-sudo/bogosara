""""이 성분들, 무슨 일을 하나요?" — 전성분의 배합목적(purpose)을 세어 카드로 보여준다.

라벨링(A안, 사용자 확인 완료): 새 카테고리를 만들지 않고 원본 purpose_name을 최소 가공만
해서 쓴다 — 괄호 안이 "기타"/"기능성화장품"이면 버리고 base 이름, 아니면 괄호 안을 쓴다
(frontend/src/api.ts의 extractPurposeLabel과 동일 규칙, 백엔드에도 그대로 재구현).
그래서 "보습제"↔"피부보습제"처럼 비슷한 개념이 원본 표기가 다르면 합쳐지지 않고 별도
라벨로 남는다 — 임의로 새 이름을 짓거나 합치지 않기로 한 결정.

제외 라벨(EXCLUDED_LABELS): 순수 제형/기술 성분(용제/유화제/점도조절제 등 — 괄호만 떼면
"수성"/"비수성"처럼 단독으로 뜻이 안 통하는 라벨이 되는 것들 포함)과 헤어/네일 전용
목적(스킨케어 요약과 무관) — 10개 대상 상품 실측 데이터 기준으로 사람이 확인한 목록.
"""
import json
import re
from collections import Counter, defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ingredient_purpose import IngredientPurpose
from app.models.product import Product
from app.models.purpose import Purpose
from app.schemas.purpose_count import PurposeCount

_NON_LABEL_PAREN_VALUES = {"기타", "기능성화장품"}

_EXCLUDED_LABELS = {
    # 순수 제형/기술 성분 — 사용자 효능이 아니라 만드는 방식에 관한 것
    "용제", "유화제", "유화안정제", "수성", "비수성", "수렴제", "pH 조정제",
    "금속이온봉쇄제", "피막형성제", "증량제", "결합제", "벌킹제", "불투명화제",
    "비계면활성", "비계면활성제", "흡수제", "변색방지제", "변성제", "안티케이킹제",
    "가소제", "감미제", "점도감소제",
    # 헤어/네일 전용 — 스킨케어 성분 요약과 무관
    "헤어컨디셔닝제", "모발컨디셔닝제", "모발고정제",
}


def extract_purpose_label(purpose_name: str) -> str:
    """"피부컨디셔닝제(보습제)" -> "보습제", "주름개선(기능성화장품)" -> "주름개선",
    "피부컨디셔닝제(기타)" -> "피부컨디셔닝제", "착향제" -> "착향제" (그대로)."""
    m = re.match(r"^(.*?)\(([^)]*)\)\s*$", purpose_name)
    if not m:
        return purpose_name.strip()
    base, paren = m.group(1).strip(), m.group(2).strip()
    return base if paren in _NON_LABEL_PAREN_VALUES else paren


def compute_purpose_counts(product: Product, db: Session, *, limit: int = 6) -> list[PurposeCount]:
    """카드에 보여줄 배합목적 카운트. 분모는 전성분 개수, 분자는 그 라벨에 해당하는
    "성분 개수"(같은 성분이 근본적으로 같은 라벨을 여러 번 갖고 있어도 1번만 센다 —
    예: 한 성분이 "피부컨디셔닝제"와 "피부컨디셔닝제(기타)"를 동시에 가지면 둘 다
    같은 라벨이라 1개로만 카운트). 다만 한 성분이 서로 다른 라벨(예: 보습제와
    산화방지제)에 걸리면 그건 각 라벨에서 각각 카운트된다(중복 허용, 사용자 요구사항).

    표시 순서: product.key_purposes(기존 core_ingredient_selector 큐레이션)에 있는
    문구와 겹치는(부분 문자열로 포함되는) 라벨을 우선 배치하고, 그다음은 개수 많은 순.
    """
    ingredient_ids = [pi.ingredient_id for pi in product.product_ingredients]
    total = len(ingredient_ids)
    if total == 0:
        return []

    rows = db.execute(
        select(IngredientPurpose.ingredient_id, Purpose.purpose_name)
        .join(Purpose, IngredientPurpose.purpose_id == Purpose.purpose_id)
        .where(IngredientPurpose.ingredient_id.in_(ingredient_ids))
    ).all()

    ingredients_by_label: dict[str, set[int]] = defaultdict(set)
    for ingredient_id, purpose_name in rows:
        label = extract_purpose_label(purpose_name)
        if label in _EXCLUDED_LABELS:
            continue
        ingredients_by_label[label].add(ingredient_id)

    if not ingredients_by_label:
        return []

    key_purposes = json.loads(product.key_purposes) if product.key_purposes else []

    def is_priority(label: str) -> bool:
        return any(kp in label or label in kp for kp in key_purposes)

    counts = Counter({label: len(ids) for label, ids in ingredients_by_label.items()})
    ordered = sorted(counts.items(), key=lambda item: (not is_priority(item[0]), -item[1]))

    return [PurposeCount(label=label, count=count, total=total) for label, count in ordered[:limit]]
