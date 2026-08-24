"""Qwen 연결 전, LLM에 실제로 넘어갈 입력(근거 묶음)을 조립해서 파일로 덤프한다.
아직 LLM 호출은 하지 않는다 — prompts/*.md 템플릿에 실제 값을 채워서 눈으로 확인하는 용도.

Usage:
    python -m scripts.build_llm_input [--ingredient-id 1938] [--product-id p-69250fe7725a]

출력:
    prompts/examples/ingredient_input.json   — 성분 프롬프트에 들어갈 근거 묶음(JSON)
    prompts/examples/ingredient_prompt.md    — 위 근거를 ingredient_summary.md에 채운 최종 프롬프트
    prompts/examples/product_input.json      — 제품 프롬프트에 들어갈 근거 묶음(JSON)
    prompts/examples/product_prompt.md       — 위 근거를 product_summary.md에 채운 최종 프롬프트
"""
import argparse
import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import SessionLocal
from app.models.ingredient import Ingredient
from app.models.ingredient_purpose import IngredientPurpose
from app.models.ingredient_relation import IngredientRelation
from app.models.ingredient_skin_score import IngredientSkinScore
from app.models.product import Product
from app.models.product_concern import ProductConcern

PROMPTS_DIR = Path(__file__).resolve().parents[1] / "prompts"
OUT_DIR = PROMPTS_DIR / "examples"


def _parse_json_list(raw: str | None) -> list[str]:
    """product.key_ingredients/key_purposes는 core_ingredient_selector가 채운 JSON 배열
    문자열이다 (app/schemas/product.py의 _parse_json_list validator와 같은 규칙)."""
    if not raw:
        return []
    return json.loads(raw)


def build_ingredient_input(db, ingredient_id: int, product_id: str) -> dict:
    """성분 하나 + (그 성분이 들어있는) 제품 맥락을 묶은, ingredient_summary.md용 입력."""
    ingredient = db.get(Ingredient, ingredient_id)
    product = db.get(Product, product_id)
    key_names = set(_parse_json_list(product.key_ingredients))

    purposes = db.scalars(
        select(IngredientPurpose)
        .options(selectinload(IngredientPurpose.purpose))
        .where(IngredientPurpose.ingredient_id == ingredient_id)
    ).all()

    relations = db.scalars(
        select(IngredientRelation)
        .options(
            selectinload(IngredientRelation.ingredient_a),
            selectinload(IngredientRelation.ingredient_b),
        )
        .where(
            (IngredientRelation.ingredient_a_id == ingredient_id)
            | (IngredientRelation.ingredient_b_id == ingredient_id)
        )
    ).all()

    skin_scores = db.scalars(
        select(IngredientSkinScore).where(IngredientSkinScore.ingredient_id == ingredient_id)
    ).all()

    concerns = db.scalars(
        select(ProductConcern).where(ProductConcern.product_id == product_id)
    ).all()

    return {
        "product": {
            "product_name": product.product_name,
            "brand": product.brand,
            "category": product.category,
            "key_ingredients": sorted(key_names),
            "key_purposes": _parse_json_list(product.key_purposes),
            "product_concern": [c.concern for c in concerns],
        },
        "ingredient": {
            "name_kr": ingredient.name_kr,
            "name_en": ingredient.name_en,
            "safety_level": ingredient.safety_level,
            "is_key": ingredient.name_kr in key_names,
            "purposes": [
                {"name": ip.purpose.purpose_name, "description": ip.purpose.description}
                for ip in purposes
            ],
            "relations": [
                {
                    "relation_type": r.relation_type,
                    "related_ingredient": (
                        r.ingredient_b if r.ingredient_a_id == ingredient_id else r.ingredient_a
                    ).name_kr,
                    "note": r.user_message,
                }
                for r in relations
            ],
            # 2026-08-21 개편: score(-3~+3) 대신 is_risk(위험/궁합 여부)만 남았다
            # (app/models/ingredient_skin_score.py 참고).
            "skin_scores": [
                {
                    "skin_type": s.skin_type,
                    "is_risk": s.is_risk,
                    "function": s.function,
                    "caution": s.caution,
                }
                for s in skin_scores
            ],
        },
    }


def build_product_input(db, product_id: str) -> dict:
    """제품의 핵심 성분 구성을 묶은, product_summary.md용 입력."""
    product = db.get(Product, product_id)
    key_names = _parse_json_list(product.key_ingredients)
    concerns = db.scalars(
        select(ProductConcern).where(ProductConcern.product_id == product_id)
    ).all()

    key_ingredients_detail = []
    key_ingredient_ids: list[int] = []
    for name in key_names:
        ing = db.scalars(select(Ingredient).where(Ingredient.name_kr == name)).first()
        if ing is None:
            continue
        key_ingredient_ids.append(ing.ingredient_id)
        purposes = db.scalars(
            select(IngredientPurpose)
            .options(selectinload(IngredientPurpose.purpose))
            .where(IngredientPurpose.ingredient_id == ing.ingredient_id)
        ).all()
        top_purpose = purposes[0].purpose.purpose_name if purposes else None
        key_ingredients_detail.append({"name": name, "purpose": top_purpose})

    # 핵심 성분끼리 실제로 걸린 관계만 — "왜 이 조합인지"에 쓸 수 있는 근거만 남긴다.
    relations = []
    if key_ingredient_ids:
        rels = db.scalars(
            select(IngredientRelation)
            .options(
                selectinload(IngredientRelation.ingredient_a),
                selectinload(IngredientRelation.ingredient_b),
            )
            .where(
                IngredientRelation.ingredient_a_id.in_(key_ingredient_ids)
                | IngredientRelation.ingredient_b_id.in_(key_ingredient_ids)
            )
        ).all()
        for r in rels:
            if r.ingredient_a_id in key_ingredient_ids and r.ingredient_b_id in key_ingredient_ids:
                relations.append(
                    {
                        "relation_type": r.relation_type,
                        "ingredient_a": r.ingredient_a.name_kr,
                        "ingredient_b": r.ingredient_b.name_kr,
                        "note": r.user_message,
                    }
                )

    return {
        "product_name": product.product_name,
        "brand": product.brand,
        "category": product.category,
        "key_ingredients": key_ingredients_detail,
        "product_concern": [c.concern for c in concerns],
        "key_ingredient_relations": relations,
    }


def render_prompt(template_path: Path, input_data: dict) -> str:
    template = template_path.read_text(encoding="utf-8")
    input_json = json.dumps(input_data, ensure_ascii=False, indent=2)
    return template.replace("{input_json}", input_json)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ingredient-id", type=int, default=1938, help="기본값: 나이아신아마이드")
    parser.add_argument("--product-id", default="p-69250fe7725a", help="기본값: 아누아 세럼")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    db = SessionLocal()
    try:
        ingredient_input = build_ingredient_input(db, args.ingredient_id, args.product_id)
        product_input = build_product_input(db, args.product_id)
    finally:
        db.close()

    (OUT_DIR / "ingredient_input.json").write_text(
        json.dumps(ingredient_input, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUT_DIR / "product_input.json").write_text(
        json.dumps(product_input, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUT_DIR / "ingredient_prompt.md").write_text(
        render_prompt(PROMPTS_DIR / "ingredient_summary.md", ingredient_input), encoding="utf-8"
    )
    (OUT_DIR / "product_prompt.md").write_text(
        render_prompt(PROMPTS_DIR / "product_summary.md", product_input), encoding="utf-8"
    )

    print(f"ingredient input  -> {OUT_DIR / 'ingredient_input.json'}")
    print(f"ingredient prompt -> {OUT_DIR / 'ingredient_prompt.md'}")
    print(f"product input     -> {OUT_DIR / 'product_input.json'}")
    print(f"product prompt    -> {OUT_DIR / 'product_prompt.md'}")


if __name__ == "__main__":
    main()
