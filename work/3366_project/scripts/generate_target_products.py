"""지정 9개 제품 + 그 제품들에 들어있는 모든 성분에 대해 Qwen(vLLM)으로 LLM이 만들어야 하는
값만 생성해서 DB에 캐싱하는 일회성 배치 스크립트.

scripts/generate_llm_summaries.py --key-ingredients는 큐레이션된 핵심 성분(보통 5개)만 도는데,
이 스크립트는 대상 제품의 "전성분"(product_ingredient 전체)을 대상으로 한다 — 여러 제품에 겹치는
성분은 한 번만 생성하고 나머지 제품에서는 캐시(이미 llm_summary가 있음)로 재사용한다.

생성 대상:
  - 성분별 llm_summary 6필드(summary_text/benefit_text/usage_reason_text/caution_text/
    caution_group_text/combo_recommendation). caution_text는 safety_level이 있을 때만,
    combo_recommendation은 relations가 있을 때만, caution_group_text는 skin_scores에
    is_risk=true인 항목이 있을 때만 채운다 — LLM이 규칙을 안 지켜도 enforce_evidence_gates()가
    한 번 더 강제한다.
  - 제품별 product.summary(one_liner) + product.composition_text.

캐시 재사용: llm_summary.summary_text가 이미 있는 성분, product.summary와
composition_text가 둘 다 이미 있는 제품은 LLM 호출 없이 건너뛴다.

안전장치: 성분/제품 하나마다 개별 UPSERT + commit (하나 실패해도 나머지는 계속 진행),
실패는 rollback 후 기록만 하고 다음으로 넘어간다.

Usage:
    python -m scripts.generate_target_products
    python -m scripts.generate_target_products --model Qwen/Qwen3-8B-AWQ

출력:
    logs/generate_target_products_<timestamp>.log            — 진행 로그
    logs/generate_target_products_<timestamp>_failures.json  — 실패 목록(재시도용)
"""
import argparse
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal, upsert_insert
from app.models.ingredient import Ingredient
from app.models.llm_summary import LLMSummary
from app.models.product import Product
from app.models.product_ingredient import ProductIngredient
from scripts.build_llm_input import build_ingredient_input, build_product_input, render_prompt
from scripts.generate_compare import PROMPTS_DIR, call_llm, extract_json

ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "logs"

TARGET_PRODUCT_NAMES = [
    "더마팩토리 나이아신아마이드 20% 세럼 30ml",
    "더마팩토리 리얼베라 모공세럼 30ml",
    "아누아 TXA 나이아신 흔적 세럼 30ml",
    "아누아 복숭아 70 나이아신아마이드 세럼 30ml",
    "아누아 어성초 77 B3 징크 트러블 세럼 30ml",
    "아누아 피디알엔 히알루론산 캡슐 100 세럼 30mL",
    "VT 리들샷 100 에센스 30ml",
    "VT 리들샷 300 에센스 50ml",
    "VT 피디알엔 에센스 100 30ml",
]

LLM_SUMMARY_FIELDS = [
    "summary_text",
    "benefit_text",
    "usage_reason_text",
    "combo_recommendation",
    "caution_text",
    "caution_group_text",
]

logger = logging.getLogger("generate_target_products")


def setup_logging(log_path: Path) -> None:
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(message)s", "%H:%M:%S")
    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setFormatter(fmt)
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    logger.addHandler(fh)
    logger.addHandler(sh)


def enforce_evidence_gates(parsed: dict, input_data: dict) -> dict:
    """LLM이 프롬프트 규칙(근거 없으면 빈 문자열)을 안 지켰을 경우를 대비해, 코드 레벨에서
    한 번 더 강제한다: safety_level 없으면 caution_text, relations 없으면 combo_recommendation,
    is_risk 성분이 없으면 caution_group_text를 무조건 빈 문자열로 덮어쓴다."""
    out = dict(parsed)
    ing = input_data["ingredient"]
    if not ing.get("safety_level"):
        out["caution_text"] = ""
    if not ing.get("relations"):
        out["combo_recommendation"] = ""
    if not any(s.get("is_risk") for s in ing.get("skin_scores", [])):
        out["caution_group_text"] = ""
    return out


def generate_ingredient(db: Session, ingredient_id: int, product_id: str, model: str) -> bool:
    """성분 하나 생성 + UPSERT + commit. 성공하면 True, JSON 파싱 실패면 False.
    (호출 자체의 예외는 상위에서 처리하도록 그대로 전파한다.)"""
    ingredient = db.get(Ingredient, ingredient_id)
    input_data = build_ingredient_input(db, ingredient_id, product_id)
    prompt = render_prompt(PROMPTS_DIR / "ingredient_summary.md", input_data)

    raw, elapsed = call_llm(model, prompt, num_predict=700)
    parsed = extract_json(raw)
    if parsed is None:
        logger.warning(
            f"  -> {elapsed:.1f}s FAIL(parse) ingredient_id={ingredient_id} "
            f"'{ingredient.name_kr}' 원문: {raw[:150]!r}"
        )
        return False

    parsed = enforce_evidence_gates(parsed, input_data)
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
    logger.info(f"  -> {elapsed:.1f}s OK ingredient_id={ingredient_id} '{ingredient.name_kr}'")
    return True


def generate_product_summary(
    db: Session, product_id: str, model: str, need_summary: bool, need_composition: bool
) -> bool:
    """제품 요약 생성 + commit. 이미 채워진 필드는 새로 생성된 값이 있어도 덮어쓰지 않는다."""
    product = db.get(Product, product_id)
    input_data = build_product_input(db, product_id)
    prompt = render_prompt(PROMPTS_DIR / "product_summary.md", input_data)
    raw, elapsed = call_llm(model, prompt, num_predict=700)
    parsed = extract_json(raw)
    if parsed is None:
        logger.warning(
            f"  -> {elapsed:.1f}s FAIL(parse) product '{product.product_name}' 원문: {raw[:150]!r}"
        )
        return False

    if need_summary and parsed.get("one_liner"):
        product.summary = parsed["one_liner"]
    if need_composition and parsed.get("composition_text"):
        product.composition_text = parsed["composition_text"]
    product.summary_generated_at = datetime.now(timezone.utc)
    db.commit()
    logger.info(f"  -> {elapsed:.1f}s OK product '{product.product_name}'")
    return True


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=None, help="기본값: settings.vllm_model/ollama_model")
    args = parser.parse_args()
    model = args.model or (
        settings.vllm_model if settings.llm_provider == "vllm" else settings.ollama_model
    )

    LOG_DIR.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = LOG_DIR / f"generate_target_products_{ts}.log"
    failures_path = LOG_DIR / f"generate_target_products_{ts}_failures.json"
    setup_logging(log_path)

    logger.info(f"provider={settings.llm_provider} model={model}")
    logger.info(f"대상 제품 {len(TARGET_PRODUCT_NAMES)}개")

    db = SessionLocal()
    started = time.time()
    failures: list[dict] = []
    per_product_report: list[dict] = []
    processed_ingredient_ids: set[int] = set()

    try:
        products: list[Product] = []
        for name in TARGET_PRODUCT_NAMES:
            p = db.scalars(select(Product).where(Product.product_name == name)).first()
            if p is None:
                logger.error(f"제품을 찾을 수 없음: {name!r} — 건너뜀")
                failures.append({"type": "product_not_found", "product_name": name})
                continue
            products.append(p)

        for p in products:
            logger.info(f"=== [{p.product_id}] {p.product_name} ===")
            report = {
                "product_id": p.product_id,
                "product_name": p.product_name,
                "product_summary_status": None,
                "ingredients_total": 0,
                "ingredients_generated": 0,
                "ingredients_skipped_cached": 0,
                "ingredients_skipped_shared": 0,
                "ingredients_failed": 0,
            }

            # 1) 제품 요약(one_liner + composition_text) — 필드별로 이미 채워졌으면 skip
            need_summary = not (p.summary and p.summary.strip())
            need_composition = not (p.composition_text and p.composition_text.strip())
            if not need_summary and not need_composition:
                report["product_summary_status"] = "skipped_cached"
                logger.info("  제품 요약: 이미 채워짐 — skip")
            else:
                try:
                    ok = generate_product_summary(db, p.product_id, model, need_summary, need_composition)
                    report["product_summary_status"] = "generated" if ok else "failed"
                    if not ok:
                        failures.append(
                            {
                                "type": "product",
                                "product_id": p.product_id,
                                "product_name": p.product_name,
                                "error": "json_parse_failed",
                            }
                        )
                except Exception as e:
                    db.rollback()
                    report["product_summary_status"] = "failed"
                    logger.exception(f"  제품 요약 생성 중 예외: {e}")
                    failures.append(
                        {
                            "type": "product",
                            "product_id": p.product_id,
                            "product_name": p.product_name,
                            "error": str(e),
                        }
                    )

            # 2) 전성분(product_ingredient 전체) — key_ingredients(큐레이션 5개)로 제한하지 않는다
            pis = db.scalars(
                select(ProductIngredient)
                .where(ProductIngredient.product_id == p.product_id)
                .order_by(ProductIngredient.label_rank.is_(None), ProductIngredient.label_rank)
            ).all()
            report["ingredients_total"] = len(pis)

            for pi in pis:
                iid = pi.ingredient_id
                ing = db.get(Ingredient, iid)
                llm = db.get(LLMSummary, iid)
                already_cached = bool(llm is not None and llm.summary_text and llm.summary_text.strip())

                if already_cached:
                    report["ingredients_skipped_cached"] += 1
                    continue
                if iid in processed_ingredient_ids:
                    report["ingredients_skipped_shared"] += 1
                    continue

                try:
                    ok = generate_ingredient(db, iid, p.product_id, model)
                    processed_ingredient_ids.add(iid)
                    if ok:
                        report["ingredients_generated"] += 1
                    else:
                        report["ingredients_failed"] += 1
                        failures.append(
                            {
                                "type": "ingredient",
                                "product_id": p.product_id,
                                "ingredient_id": iid,
                                "ingredient_name": ing.name_kr if ing else None,
                                "error": "json_parse_failed",
                            }
                        )
                except Exception as e:
                    db.rollback()
                    report["ingredients_failed"] += 1
                    logger.exception(f"  성분 생성 중 예외 ingredient_id={iid}: {e}")
                    failures.append(
                        {
                            "type": "ingredient",
                            "product_id": p.product_id,
                            "ingredient_id": iid,
                            "ingredient_name": ing.name_kr if ing else None,
                            "error": str(e),
                        }
                    )

            per_product_report.append(report)
            logger.info(
                f"  성분 {report['ingredients_total']}개 — 생성 {report['ingredients_generated']}, "
                f"캐시skip {report['ingredients_skipped_cached']}, "
                f"공유skip {report['ingredients_skipped_shared']}, "
                f"실패 {report['ingredients_failed']}"
            )
    finally:
        db.close()

    total_elapsed = time.time() - started
    failures_path.write_text(json.dumps(failures, ensure_ascii=False, indent=2), encoding="utf-8")

    logger.info("")
    logger.info("========== 최종 리포트 ==========")
    for r in per_product_report:
        logger.info(
            f"[{r['product_id']}] {r['product_name']}: "
            f"제품요약={r['product_summary_status']}, "
            f"성분 생성={r['ingredients_generated']}/{r['ingredients_total']} "
            f"(캐시skip {r['ingredients_skipped_cached']}, 공유skip {r['ingredients_skipped_shared']}, "
            f"실패 {r['ingredients_failed']})"
        )
    total_generated = sum(r["ingredients_generated"] for r in per_product_report)
    total_failed = sum(r["ingredients_failed"] for r in per_product_report)
    product_failed = sum(1 for r in per_product_report if r["product_summary_status"] == "failed")
    logger.info(f"총 소요시간: {total_elapsed/60:.1f}분 ({total_elapsed:.0f}초)")
    logger.info(f"성분 총 생성 성공: {total_generated}, 총 실패: {total_failed}")
    logger.info(f"제품 요약 실패: {product_failed}")
    logger.info(f"실패 목록: {len(failures)}건 -> {failures_path}")
    logger.info(f"로그 파일: {log_path}")


if __name__ == "__main__":
    main()
