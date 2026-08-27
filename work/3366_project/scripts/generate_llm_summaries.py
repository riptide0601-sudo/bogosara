"""LLM(기본 gemma2:2b) 요약을 실제로 생성해서 DB에 UPSERT 저장한다.

scripts/generate_compare.py(비교용, DB 안 건드림)와 달리 이 스크립트는 진짜 저장한다:
  - 성분 하나 → llm_summary 6필드 UPSERT
  - 제품 하나 → product.summary(one_liner) + product.composition_text UPSERT

CPU 로컬 환경이라 전체 배치가 아니라 지정한 성분/제품만 소량 생성하는 용도.

Usage:
    python -m scripts.generate_llm_summaries --ingredient-id 1938
    python -m scripts.generate_llm_summaries --product-id p-69250fe7725a
    python -m scripts.generate_llm_summaries --product-id p-69250fe7725a --key-ingredients
    python -m scripts.generate_llm_summaries --product-id p-69250fe7725a --key-ingredients --model gemma2:2b
"""
import argparse
from datetime import datetime, timezone

from sqlalchemy import or_, select

from app.config import settings
from app.database import SessionLocal, upsert_insert
from app.models.ingredient import Ingredient
from app.models.llm_summary import LLMSummary
from app.models.product import Product
from app.models.product_ingredient import ProductIngredient
from scripts.build_llm_input import build_ingredient_input, build_product_input, render_prompt, _parse_json_list
from scripts.generate_compare import PROMPTS_DIR, call_llm, extract_json

LLM_SUMMARY_FIELDS = [
    "summary_text",
    "benefit_text",
    "usage_reason_text",
    "combo_recommendation",
    "caution_text",
    "caution_group_text",
]


def generate_and_save_ingredient(db, ingredient_id: int, product_id: str, model: str) -> None:
    ingredient = db.get(Ingredient, ingredient_id)
    input_data = build_ingredient_input(db, ingredient_id, product_id)
    prompt = render_prompt(PROMPTS_DIR / "ingredient_summary.md", input_data)

    print(f"[{settings.llm_provider}:{model}] '{ingredient.name_kr}' 생성 중...")
    raw, elapsed = call_llm(model, prompt)
    parsed = extract_json(raw)

    if parsed is None:
        print(f"  -> {elapsed:.1f}s, JSON 파싱 실패 — 저장하지 않음. 원문 앞부분: {raw[:200]!r}")
        return

    values = {field: parsed.get(field) or None for field in LLM_SUMMARY_FIELDS}
    generated_at = datetime.now(timezone.utc)
    stmt = (
        upsert_insert(LLMSummary)
        .values(ingredient_id=ingredient_id, summary_generated_at=generated_at, **values)
        .on_conflict_do_update(
            index_elements=["ingredient_id"],
            set_={**values, "summary_generated_at": generated_at},
        )
    )
    db.execute(stmt)
    db.commit()
    print(f"  -> {elapsed:.1f}s, 저장 완료 (ingredient_id={ingredient_id})")


def generate_and_save_product_summary(db, product_id: str, model: str) -> None:
    product = db.get(Product, product_id)
    input_data = build_product_input(db, product_id)
    prompt = render_prompt(PROMPTS_DIR / "product_summary.md", input_data)

    print(f"[{settings.llm_provider}:{model}] 제품 요약 '{product.product_name}' 생성 중...")
    raw, elapsed = call_llm(model, prompt)
    parsed = extract_json(raw)

    if parsed is None:
        print(f"  -> {elapsed:.1f}s, JSON 파싱 실패 — 저장하지 않음. 원문 앞부분: {raw[:200]!r}")
        return

    product.summary = parsed.get("one_liner") or product.summary
    product.composition_text = parsed.get("composition_text") or product.composition_text
    product.summary_generated_at = datetime.now(timezone.utc)
    db.commit()
    print(f"  -> {elapsed:.1f}s, 저장 완료 (product_id={product_id})")


def find_empty_ingredient_ids(db, limit: int) -> list[int]:
    """llm_summary가 아예 없거나 summary_text가 비어있는 성분 id를 limit개까지."""
    stmt = (
        select(Ingredient.ingredient_id)
        .outerjoin(LLMSummary, LLMSummary.ingredient_id == Ingredient.ingredient_id)
        .where(or_(LLMSummary.ingredient_id.is_(None), LLMSummary.summary_text.is_(None)))
        .order_by(Ingredient.ingredient_id)
        .limit(limit)
    )
    return list(db.scalars(stmt).all())


def pick_context_product_id(db, ingredient_id: int) -> str | None:
    """배치 생성용 — 이 성분이 들어있는 제품 중 label_rank가 가장 앞선(=가장 두드러진) 것을
    프롬프트 맥락(product context)으로 고른다. 연결된 제품이 없으면 None."""
    stmt = (
        select(ProductIngredient.product_id)
        .where(ProductIngredient.ingredient_id == ingredient_id)
        .order_by(ProductIngredient.label_rank.is_(None), ProductIngredient.label_rank)
        .limit(1)
    )
    return db.scalars(stmt).first()


def run_batch_empty(db, limit: int, model: str) -> None:
    ingredient_ids = find_empty_ingredient_ids(db, limit)
    print(f"[배치] llm_summary 비어있는 성분 {len(ingredient_ids)}개 대상 (요청 {limit}개)")
    ok, skipped, failed = 0, 0, 0
    for i, ingredient_id in enumerate(ingredient_ids, 1):
        product_id = pick_context_product_id(db, ingredient_id)
        if product_id is None:
            print(f"  [{i}/{len(ingredient_ids)}] ingredient_id={ingredient_id} 건너뜀 (연결된 제품 없음)")
            skipped += 1
            continue
        try:
            generate_and_save_ingredient(db, ingredient_id, product_id, model)
            ok += 1
        except Exception as e:
            db.rollback()
            failed += 1
            print(f"  [{i}/{len(ingredient_ids)}] ingredient_id={ingredient_id} 실패: {e}")
    print(f"[배치] 완료 — 성공 {ok}, 건너뜀 {skipped}, 실패 {failed} (대상 {len(ingredient_ids)})")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ingredient-id", type=int, help="이 성분 하나만 생성·저장")
    parser.add_argument("--product-id", help="제품 요약(one_liner+composition_text) 생성·저장 대상")
    parser.add_argument(
        "--key-ingredients",
        action="store_true",
        help="--product-id의 key_ingredients(핵심 성분)를 전부 순회 생성·저장",
    )
    parser.add_argument(
        "--batch-empty",
        type=int,
        metavar="N",
        help="llm_summary가 비어있는 성분을 N개까지 순회 생성 (하나 실패해도 나머지 계속)",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="기본값: provider=vllm이면 settings.vllm_model, 아니면 settings.ollama_model",
    )
    args = parser.parse_args()

    model = args.model or (
        settings.vllm_model if settings.llm_provider == "vllm" else settings.ollama_model
    )

    if not args.ingredient_id and not args.product_id and not args.batch_empty:
        raise SystemExit("--ingredient-id / --product-id / --batch-empty 중 하나는 지정해야 합니다")

    db = SessionLocal()
    try:
        if args.batch_empty:
            run_batch_empty(db, args.batch_empty, model)
        if args.ingredient_id:
            product_id = args.product_id or None
            if product_id is None:
                raise SystemExit("--ingredient-id는 맥락이 될 --product-id도 함께 필요합니다")
            generate_and_save_ingredient(db, args.ingredient_id, product_id, model)

        if args.product_id and not args.ingredient_id:
            generate_and_save_product_summary(db, args.product_id, model)

        if args.key_ingredients:
            if not args.product_id:
                raise SystemExit("--key-ingredients는 --product-id가 필요합니다")
            product = db.get(Product, args.product_id)
            names = _parse_json_list(product.key_ingredients)
            for name in names:
                ing = db.scalars(select(Ingredient).where(Ingredient.name_kr == name)).first()
                if ing is None:
                    print(f"  (건너뜀: '{name}' 성분을 찾을 수 없음)")
                    continue
                generate_and_save_ingredient(db, ing.ingredient_id, args.product_id, model)
    finally:
        db.close()


if __name__ == "__main__":
    main()
