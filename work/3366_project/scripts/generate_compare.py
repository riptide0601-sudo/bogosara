"""LLM 모델 비교용 생성 스크립트. DB는 절대 건드리지 않는다 — 결과는 eval/에만 저장한다.

제품 하나 + 모델 하나에 대해:
  1) 제품 요약(one_liner + composition_text) 1회 생성
  2) product.key_ingredients(core_ingredient_selector가 뽑은 핵심 성분) 각각의 llm_summary 5필드 생성
을 실행하고, 호출 시간을 기록하며, DB에서 읽은 나머지(성분 카드/배지/배합목적/relations)는
그대로 둔 채 llm_summary/summary/composition_text만 덮어쓴 "화면 그대로" JSON을 만든다.

사용:
    python -m scripts.generate_compare --product-id p-69250fe7725a --model gemma2:2b

출력:
    eval/compare_{product_id}_{model_slug}.json          (비교 기록 + 화면용 detail 포함)
    ../frontend/public/eval/compare_{product_id}_{model_slug}.json  (프론트 비교 화면이 fetch)
"""
import argparse
import copy
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from sqlalchemy import select

from app.database import SessionLocal
from app.models.product import Product
from app.routers.products import _detail_query, _to_detail
from scripts.build_llm_input import (
    build_ingredient_input,
    build_product_input,
    render_prompt,
    _parse_json_list,
)

ROOT = Path(__file__).resolve().parents[1]
PROMPTS_DIR = ROOT / "prompts"
EVAL_DIR = ROOT / "eval"
FRONTEND_PUBLIC_EVAL_DIR = ROOT.parent / "frontend" / "public" / "eval"
OLLAMA_URL = "http://localhost:11434/api/generate"

LLM_SUMMARY_FIELDS = [
    "summary_text",
    "benefit_text",
    "usage_reason_text",
    "combo_recommendation",
    "caution_text",
]


def slugify_model(model: str) -> str:
    return model.replace(":", "-").replace("/", "-")


def strip_think_blocks(text: str) -> str:
    """qwen3류 reasoning 모델이 <think>...</think>로 감싸는 사고 과정을 제거한다."""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()


def extract_json(text: str) -> dict | None:
    """모델 응답에서 JSON 객체 하나를 뽑아낸다. 실패하면 None (호출부가 폐기 처리)."""
    text = strip_think_blocks(text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # ```json ... ``` 코드펜스로 감싸져 있으면 벗겨서 재시도
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.S)
    if fenced:
        try:
            return json.loads(fenced.group(1))
        except json.JSONDecodeError:
            pass
    # 앞뒤에 잡담이 붙은 경우 첫 '{'부터 마지막 '}'까지만 시도
    brace = re.search(r"\{.*\}", text, re.S)
    if brace:
        try:
            return json.loads(brace.group(0))
        except json.JSONDecodeError:
            pass
    return None


def call_ollama(model: str, prompt: str, *, num_predict: int = 600) -> tuple[str, float]:
    start = time.time()
    resp = requests.post(
        OLLAMA_URL,
        json={
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"num_predict": num_predict, "temperature": 0.3},
        },
        timeout=600,
    )
    elapsed = time.time() - start
    resp.raise_for_status()
    return resp.json().get("response", ""), elapsed


def generate_product_summary(db, product_id: str, model: str) -> dict:
    input_data = build_product_input(db, product_id)
    prompt = render_prompt(PROMPTS_DIR / "product_summary.md", input_data)
    raw, elapsed = call_ollama(model, prompt)
    parsed = extract_json(raw)
    return {
        "input": input_data,
        "raw_response": raw,
        "parsed": parsed,
        "elapsed_seconds": round(elapsed, 1),
        "parse_ok": parsed is not None,
    }


def generate_ingredient_summary(db, ingredient_id: int, product_id: str, model: str) -> dict:
    input_data = build_ingredient_input(db, ingredient_id, product_id)
    prompt = render_prompt(PROMPTS_DIR / "ingredient_summary.md", input_data)
    raw, elapsed = call_ollama(model, prompt)
    parsed = extract_json(raw)
    return {
        "input": input_data,
        "raw_response": raw,
        "parsed": parsed,
        "elapsed_seconds": round(elapsed, 1),
        "parse_ok": parsed is not None,
    }


def overlay_detail(detail_dict: dict, product_summary: dict | None, ingredient_summaries: dict[str, dict]) -> dict:
    """DB에서 읽은 ProductDetail(dict)에 생성된 LLM 필드만 덮어쓴 사본을 반환한다."""
    merged = copy.deepcopy(detail_dict)
    if product_summary:
        merged["summary"] = product_summary.get("one_liner") or merged.get("summary")
        merged["composition_text"] = product_summary.get("composition_text") or merged.get("composition_text")

    def patch_ingredient_list(items: list[dict]) -> None:
        for item in items:
            name = item["ingredient"]["name_kr"]
            gen = ingredient_summaries.get(name)
            if not gen:
                continue
            llm = item["ingredient"].get("llm_summary") or {
                "ingredient_id": item["ingredient"]["ingredient_id"],
                "summary_generated_at": None,
            }
            for field in LLM_SUMMARY_FIELDS:
                if gen.get(field):
                    llm[field] = gen[field]
            item["ingredient"]["llm_summary"] = llm

    patch_ingredient_list(merged["ingredients"])
    patch_ingredient_list(merged["top_ingredients"])
    return merged


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--product-id", required=True)
    parser.add_argument("--model", required=True)
    args = parser.parse_args()

    db = SessionLocal()
    try:
        product = db.get(Product, args.product_id)
        if product is None:
            raise SystemExit(f"product not found: {args.product_id}")
        key_names = _parse_json_list(product.key_ingredients)

        # DB 그대로의 ProductDetail(성분 카드/배지/배합목적/relations 전부 포함) — 화면 베이스.
        detail_obj = _to_detail(
            db.scalars(_detail_query().where(Product.product_id == args.product_id)).first(), db
        )
        detail_dict = json.loads(detail_obj.model_dump_json())

        print(f"[{args.model}] 제품 요약 생성 중...")
        product_result = generate_product_summary(db, args.product_id, args.model)
        print(f"  -> {product_result['elapsed_seconds']}s, parse_ok={product_result['parse_ok']}")

        from app.models.ingredient import Ingredient

        ingredient_results: dict[str, dict] = {}
        for name in key_names:
            ing = db.scalars(select(Ingredient).where(Ingredient.name_kr == name)).first()
            if ing is None:
                print(f"  (건너뜀: '{name}' 성분을 찾을 수 없음)")
                continue
            print(f"[{args.model}] 핵심 성분 '{name}' 요약 생성 중...")
            result = generate_ingredient_summary(db, ing.ingredient_id, args.product_id, args.model)
            print(f"  -> {result['elapsed_seconds']}s, parse_ok={result['parse_ok']}")
            ingredient_results[name] = result

        merged_detail = overlay_detail(
            detail_dict,
            product_result["parsed"],
            {name: r["parsed"] for name, r in ingredient_results.items() if r["parsed"]},
        )

        total_seconds = product_result["elapsed_seconds"] + sum(
            r["elapsed_seconds"] for r in ingredient_results.values()
        )

        output = {
            "product_id": args.product_id,
            "model": args.model,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_elapsed_seconds": round(total_seconds, 1),
            "product_summary": product_result,
            "ingredient_summaries": ingredient_results,
            "detail": merged_detail,
        }

        EVAL_DIR.mkdir(parents=True, exist_ok=True)
        FRONTEND_PUBLIC_EVAL_DIR.mkdir(parents=True, exist_ok=True)
        slug = slugify_model(args.model)
        filename = f"compare_{args.product_id}_{slug}.json"
        text = json.dumps(output, ensure_ascii=False, indent=2)
        (EVAL_DIR / filename).write_text(text, encoding="utf-8")
        (FRONTEND_PUBLIC_EVAL_DIR / filename).write_text(text, encoding="utf-8")

        print(f"done. total {total_seconds:.1f}s -> {EVAL_DIR / filename}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
