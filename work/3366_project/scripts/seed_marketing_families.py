"""ingredient_family / ingredient_family_member를 채운다.

지금은 "마케팅 용어 검증" 대상 10개 상품의 전성분에서 실제로 발견된 성분만 담는다(전체
22,067개 성분 기준 전수 조사는 다음 범위 확장 때). 근거는 docs/marketing_terms/alias_table.csv
작업에서 사람이 확인한 것과 동일 — 어근 매칭(1차) + 배합목적/DB 정의문 교차검증(2차), 애매한
건(PDRN↔Sodium DNA 등) 사용자 확인 후에만 반영했다.

이 테이블(ingredient_family/ingredient_family_member)은 "비슷한 제품과 비교하면" 기능
(scripts/backfill_ingredient_families.py)과 같이 쓴다 — 겹치는 6개 계열은 그쪽 family_name
표기(예: "판토텐산(B5) 계열", "비피다 계열")를 그대로 따라서 같은 계열이 두 행으로 쪼개지지
않게 한다. NMN/EGF 계열은 이 기능 전용이라 이름 충돌이 없다.

Usage:
    python -m scripts.seed_marketing_families
"""
from app.database import SessionLocal, upsert_insert
from app.models.ingredient import Ingredient
from app.models.ingredient_family import IngredientFamily
from app.models.ingredient_family_member import IngredientFamilyMember
from app.models.product import Product

TARGET_PRODUCT_IDS = [
    "p-cb5c0bb61e60",
    "p-f809f0cf2a0f",
    "p-12b96e48b5ee",
    "p-8d07a757af76",
    "p-7506d24a70c0",
    "p-39470481ac04",
    "p-3f286a959089",
    "p-fdd1f5a784ee",
    "p-b647edef067b",
    "p-766b8f4c51d2",
]

EGF_ID = 7477  # 에스에이치-올리고펩타이드-1 — DB 정의문 근거, 사용자 확인 완료

# name -> (marketing_terms, basis_note, [(match_type, kr_roots, en_roots, exclude_ids, explicit_ids), ...])
FAMILIES: dict[str, dict] = {
    "히알루론산 계열": {
        "marketing_terms": ["히알루론산", "히알"],
        "basis_note": "어근: 하이알루로/히알루론, Hyaluron",
        "rules": [("정확(어근일치)", ["하이알루로", "히알루론"], ["Hyaluron"], set(), set())],
    },
    "판토텐산(B5) 계열": {
        "marketing_terms": ["판토텐산", "B5"],
        "basis_note": "어근: 판테놀/판토텐, Panthen/Pantothen",
        "rules": [("정확(어근일치)", ["판테놀", "판토텐"], ["Panthen", "Pantothen"], set(), set())],
    },
    "비타민C 계열": {
        "marketing_terms": ["비타민씨", "비타민C", "비타민 C"],
        "basis_note": "어근: 아스코빌/아스코르빈/아스코르브, Ascorb",
        "rules": [("정확(어근일치)", ["아스코빌", "아스코르빈", "아스코르브"], ["Ascorb"], set(), set())],
    },
    "콜라겐 계열": {
        "marketing_terms": ["콜라겐"],
        "basis_note": "정확: 어근 콜라겐/Collagen. 유연물질: 콜라겐 직접 함유 아님 — 콜라겐 합성 촉진 펩타이드",
        "rules": [
            ("정확(어근일치)", ["콜라겐"], ["Collagen"], set(), set()),
            ("유연물질(관련이지만 다른 물질)", ["트라이펩타이드", "펩타이드"], ["Peptide"], {EGF_ID}, set()),
        ],
    },
    "비피다 계열": {
        "marketing_terms": ["비피다"],
        "basis_note": "어근: 비피다, Bifida",
        "rules": [("정확(어근일치)", ["비피다"], ["Bifida"], set(), set())],
    },
    "마데카소사이드 계열": {
        "marketing_terms": ["마데카소사이드"],
        "basis_note": "정확: 어근 마데카소사이드/Madecassoside. 유연물질: 같은 병풀(Centella Asiatica) 유래지만 화학적으로 다른 화합물",
        "rules": [
            ("정확(어근일치)", ["마데카소사이드"], ["Madecassoside"], set(), set()),
            ("유연물질(관련이지만 다른 물질)", ["마데카식", "아시아티", "병풀"], ["Centella", "Asiatic"], set(), set()),
        ],
    },
    "NMN 계열": {
        "marketing_terms": ["NMN"],
        "basis_note": "어근: 니코틴아마이드모노뉴클레오타이드, Nicotinamide Mononucleotide",
        "rules": [
            (
                "정확(어근일치)",
                ["니코틴아마이드모노뉴클레오타이드"],
                ["Nicotinamide Mononucleotide"],
                set(),
                set(),
            )
        ],
    },
    "EGF 계열": {
        "marketing_terms": ["EGF"],
        "basis_note": (
            'DB summary(정의 원문)에 "상피세포성장인자(Epidermal Growth Factor)를 코딩하는 '
            '사람 유전자와 동일한 코드로 합성"이라고 명시 — 어근매칭 아닌 정의문 근거, 사용자 확인 완료'
        ),
        "rules": [("정확(DB 정의문 근거)", [], [], set(), {EGF_ID})],
    },
}


def main() -> None:
    db = SessionLocal()
    try:
        all_ing_ids: set[int] = set()
        for pid in TARGET_PRODUCT_IDS:
            product = db.get(Product, pid)
            if product is None:
                print(f"  (건너뜀: 제품을 찾을 수 없음 {pid})")
                continue
            for pi in product.product_ingredients:
                all_ing_ids.add(pi.ingredient_id)

        all_ingredients = {
            iid: db.get(Ingredient, iid) for iid in all_ing_ids
        }

        member_count = 0
        for family_name, spec in FAMILIES.items():
            stmt = (
                upsert_insert(IngredientFamily)
                .values(
                    family_name=family_name,
                    marketing_terms=spec["marketing_terms"],
                    basis_note=spec["basis_note"],
                )
                .on_conflict_do_update(
                    index_elements=["family_name"],
                    set_={
                        "marketing_terms": spec["marketing_terms"],
                        "basis_note": spec["basis_note"],
                    },
                )
            )
            db.execute(stmt)
            db.commit()
            family = db.query(IngredientFamily).filter_by(family_name=family_name).one()

            for match_type, kr_roots, en_roots, exclude_ids, explicit_ids in spec["rules"]:
                candidate_ids = set(explicit_ids)
                for iid, ing in all_ingredients.items():
                    if iid in exclude_ids:
                        continue
                    name_kr = ing.name_kr or ""
                    name_en = ing.name_en or ""
                    syn = " ".join(ing.synonyms or [])
                    if (
                        any(k in name_kr for k in kr_roots)
                        or any(e.lower() in name_en.lower() for e in en_roots)
                        or any(e.lower() in syn.lower() for e in en_roots)
                    ):
                        candidate_ids.add(iid)

                for iid in sorted(candidate_ids):
                    stmt = (
                        upsert_insert(IngredientFamilyMember)
                        .values(
                            family_id=family.family_id,
                            ingredient_id=iid,
                            match_type=match_type,
                            basis_detail=spec["basis_note"],
                        )
                        .on_conflict_do_update(
                            index_elements=["family_id", "ingredient_id"],
                            set_={"match_type": match_type, "basis_detail": spec["basis_note"]},
                        )
                    )
                    db.execute(stmt)
                    member_count += 1
            db.commit()
            print(f"{family_name}: 성분 {len(candidate_ids) if spec['rules'] else 0}건 등록")

        print(f"완료 — 계열 {len(FAMILIES)}개, 성분 매핑 {member_count}건(중복 계열-성분 upsert 포함)")
    finally:
        db.close()


if __name__ == "__main__":
    main()
