""""마케팅 용어 → 성분 계열 묶기" — 카드 앞면에 보여줄 계열 묶음 블록을 계산한다.

우선순위 규칙:
  1순위 — 상품명에 그 계열의 marketing_terms(예: "히알루론산", "PDRN")가 실제로 등장하는 계열.
          상품명에서 먼저 나오는 용어 순으로 정렬한다.
  2순위 — 상품명엔 없지만 이 제품 전성분과 실제로 매칭되는 계열(ingredient_family_member 근거).
          그중 가장 앞쪽(label_rank가 가장 낮은) 성분을 가진 계열부터.
  최종적으로 최대 `limit`개까지만 반환한다(1순위를 먼저 채우고 남으면 2순위로 채움).

근거(ingredient_family/ingredient_family_member)는 scripts/seed_marketing_families.py가
사람이 확인한 어근/정의문 매칭만 채워둔다 — 여기서는 그 근거를 읽어서 "이 제품에 실제로
들어있는 것"만 걸러낼 뿐, 새로운 매칭 판단은 하지 않는다.
"""
import json
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ingredient_family import IngredientFamily
from app.models.ingredient_family_member import IngredientFamilyMember
from app.models.product import Product
from app.schemas.marketing_family import MatchedFamily, MatchedFamilyIngredient

_DOSAGE_RE = re.compile(r"\(([\d,.]+\s*(?:ppm|ppb|%))\)", re.IGNORECASE)


def _parse_dosage(matched_text: str | None) -> str | None:
    """matched_text(예: "하이드롤라이즈드하이알루로닉애씨드(29,049ppm)")에서 용량만 뽑는다.
    괄호 안이 용량 표기가 아니거나(오탈자/미완성 OCR 등) 아예 없으면 None — 지어내지 않는다."""
    if not matched_text:
        return None
    m = _DOSAGE_RE.search(matched_text)
    return m.group(1) if m else None


def compute_matched_families(product: Product, db: Session, *, limit: int = 3) -> list[MatchedFamily]:
    ingredient_ids = [pi.ingredient_id for pi in product.product_ingredients]
    if not ingredient_ids:
        return []

    key_names = set(json.loads(product.key_ingredients)) if product.key_ingredients else set()

    members = db.scalars(
        select(IngredientFamilyMember)
        .where(IngredientFamilyMember.ingredient_id.in_(ingredient_ids))
    ).all()
    if not members:
        return []

    pi_by_ingredient = {pi.ingredient_id: pi for pi in product.product_ingredients}

    members_by_family: dict[int, list[IngredientFamilyMember]] = {}
    for m in members:
        members_by_family.setdefault(m.family_id, []).append(m)

    families = db.scalars(
        select(IngredientFamily).where(IngredientFamily.family_id.in_(members_by_family.keys()))
    ).all()

    from_name: list[tuple[int, IngredientFamily, str]] = []  # (등장 위치, family, 매칭된 용어)
    from_general: list[tuple[int, IngredientFamily]] = []  # (best label_rank, family)

    for family in families:
        fam_members = members_by_family[family.family_id]
        # marketing_terms는 "상품명 성분, 진짜 들어있나요?" 전용 필드라, "비슷한 제품과
        # 비교하면" 쪽에서만 만들어진 계열은 비어 있을 수 있다 — 그때는 항상 일반 매칭(2순위).
        # 용어가 여러 개 매칭되면(예: "비타민씨"와 "비타민C" 둘 다) 상품명에서 더 먼저
        # 나오는 쪽을 대표 용어로 쓴다 — 형광펜 표시가 그 위치 기준이라 하나로 정해야 한다.
        matches = [
            (product.product_name.find(term), term)
            for term in (family.marketing_terms or [])
            if term in product.product_name
        ]
        if matches:
            best_pos, best_term = min(matches, key=lambda t: t[0])
            from_name.append((best_pos, family, best_term))
        else:
            ranks = [
                pi_by_ingredient[m.ingredient_id].label_rank
                for m in fam_members
                if pi_by_ingredient[m.ingredient_id].label_rank is not None
            ]
            best_rank = min(ranks) if ranks else 10**9
            from_general.append((best_rank, family))

    from_name.sort(key=lambda t: t[0])
    from_general.sort(key=lambda t: t[0])

    ordered_families = [(f, True, term) for _, f, term in from_name] + [
        (f, False, None) for _, f in from_general
    ]
    ordered_families = ordered_families[:limit]

    result: list[MatchedFamily] = []
    for family, from_product_name, matched_term in ordered_families:
        fam_members = sorted(
            members_by_family[family.family_id],
            key=lambda m: (
                pi_by_ingredient[m.ingredient_id].label_rank is None,
                pi_by_ingredient[m.ingredient_id].label_rank,
            ),
        )
        ingredients = []
        for m in fam_members:
            pi = pi_by_ingredient[m.ingredient_id]
            ingredients.append(
                MatchedFamilyIngredient(
                    ingredient_id=m.ingredient_id,
                    name_kr=pi.ingredient.name_kr,
                    label_rank=pi.label_rank,
                    dosage=_parse_dosage(pi.matched_text),
                    # "비슷한 제품과 비교하면" 쪽(scripts/backfill_ingredient_families.py)이
                    # 만든 행은 match_type이 비어 있다 — 그쪽도 어근 매칭이 근거라 "정확"으로
                    # 취급한다(둘 다 같은 방식, 우리 쪽만 정확/유연물질을 더 세분화했을 뿐).
                    match_type=m.match_type or "정확(어근일치)",
                    is_key_ingredient=pi.ingredient.name_kr in key_names,
                )
            )
        result.append(
            MatchedFamily(
                family_id=family.family_id,
                name=family.family_name,
                from_product_name=from_product_name,
                matched_term=matched_term,
                ingredients=ingredients,
            )
        )
    return result
