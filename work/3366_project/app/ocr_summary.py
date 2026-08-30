"""스캔(OCR) 결과에 대한 실시간 제품 요약(one_liner/composition_text) 생성.

검색 흐름(product.summary/product.composition_text)은 scripts/generate_target_products.py가
등록된 Product를 대상으로 미리 배치 생성해 캐싱해두지만, 스캔은 등록된 Product 행이 없어
그 캐시가 원천적으로 존재할 수 없다 — 그래서 스캔 결과 화면에서만, 이 모듈이 같은
prompts/product_summary.md로 그 자리에서(요청 처리 중) LLM을 호출한다.

app/llm_client.py(레거시 Ollama 전용, 자체 프롬프트·플레인 텍스트 출력)와는 별개 경로다.
여기는 scripts/generate_compare.py가 쓰는 vLLM/Qwen 호출 방식(OpenAI SDK, chat completions,
JSON 출력)과 prompts/product_summary.md를 그대로 따른다 — 검색 흐름과 톤·형식을 맞추기
위해서다. scripts/는 배치 도구 계층이라 app/이 거꾸로 거기 의존하지 않도록, 필요한 호출
로직만 이 모듈에 옮겨왔다(코드 중복보다 계층 방향을 우선했다).
"""
import json
import re
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.core_ingredient_selector import analyze_product, load_purpose_db_from_db
from app.models.ingredient import Ingredient
from app.models.ingredient_relation import IngredientRelation

_PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "product_summary.md"

# 이 정도는 있어야 "핵심 성분 구성"을 요약할 근거가 된다고 본다 — 너무 적으면(예: OCR
# 오독으로 1~2개만 인식) 부정확한 요약을 만들 근거가 없어 아예 생성하지 않는다.
_MIN_INGREDIENTS_FOR_SUMMARY = 3


def _strip_think_blocks(text: str) -> str:
    """qwen3류 reasoning 모델이 <think>...</think>로 감싸는 사고 과정을 제거한다."""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()


def _extract_json(text: str) -> dict | None:
    """모델 응답에서 JSON 객체 하나를 뽑아낸다. 실패하면 None(호출부가 폐기 처리)."""
    text = _strip_think_blocks(text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.S)
    if fenced:
        try:
            return json.loads(fenced.group(1))
        except json.JSONDecodeError:
            pass
    brace = re.search(r"\{.*\}", text, re.S)
    if brace:
        try:
            return json.loads(brace.group(0))
        except json.JSONDecodeError:
            pass
    return None


def _call_vllm(prompt: str, *, max_tokens: int = 600) -> str:
    """vLLM OpenAI 호환 서버(/v1/chat/completions) 호출 — scripts/generate_compare.py의
    call_vllm()과 동일한 방식(Qwen3 thinking mode는 꺼서 <think> 블록 없이 바로 받는다)."""
    from openai import OpenAI

    client = OpenAI(base_url=settings.vllm_base_url, api_key="not-needed")
    resp = client.chat.completions.create(
        model=settings.vllm_model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        temperature=0.3,
        extra_body={"chat_template_kwargs": {"enable_thinking": False}},
    )
    return resp.choices[0].message.content or ""


def get_key_ingredients(db: Session, raw_ingredients: list[str]) -> list[str]:
    """OCR 원문 성분 목록에서 "핵심 성분" 이름을 순서대로 뽑는다 — app/core_ingredient_selector.
    analyze_product()(검색 흐름의 "핵심 성분" 카드와 동일한 필터+정렬 알고리즘, order_index
    기준)를 OCR 원문에 직접 돌린다. 검색 흐름은 이 큐레이션을 배치로 미리 계산해
    product.key_ingredients에 저장해두지만(scripts/generate_target_products.py), 스캔은
    등록된 Product가 없어 그 캐시가 없다 — 요청마다 이 함수가 그 자리에서 계산한다."""
    purpose_db = load_purpose_db_from_db(db)
    analysis = analyze_product(", ".join(raw_ingredients), purpose_db)
    return analysis["ingredients"]


def _build_input(db: Session, raw_ingredients: list[str]) -> dict:
    """OCR 원문 성분 목록 -> prompts/product_summary.md 입력.

    scripts/build_llm_input.py의 build_product_input()은 등록된 Product ORM 행이 있어야
    돌아가는데 스캔엔 그게 없다. 대신 app/core_ingredient_selector.analyze_product()
    (docstring: "OCR로 추출한 전성분표 텍스트" 처리용, 검색 흐름의 "핵심 성분" 큐레이션과
    동일 알고리즘)를 OCR 원문에 직접 돌려 같은 방식으로 핵심 성분을 뽑는다.
    """
    purpose_db = load_purpose_db_from_db(db)
    analysis = analyze_product(", ".join(raw_ingredients), purpose_db)

    # analyze_product 내부의 parse_ingredient_text가 "(1,000ppm)" 같은 괄호 표기를
    # 떼고 이름만 남기므로, 라벨 원문(농도 표기) 대조는 여기서 원본과 다시 맞춰본다.
    name_to_raw: dict[str, str] = {}
    for raw in raw_ingredients:
        cleaned = re.sub(r"\(.*?\)", "", raw).strip()
        if cleaned and cleaned not in name_to_raw:
            name_to_raw[cleaned] = raw

    detail_by_name = {item["name"]: item for item in analysis["detail"]}
    key_ingredients_detail = []
    key_ingredient_ids: list[int] = []
    for name in analysis["ingredients"]:
        item = detail_by_name.get(name, {})
        purposes = item.get("purposes") or []
        ingredient = db.scalars(select(Ingredient).where(Ingredient.name_kr == name)).first()
        if ingredient:
            key_ingredient_ids.append(ingredient.ingredient_id)
        raw = name_to_raw.get(name)
        key_ingredients_detail.append(
            {
                "name": name,
                "purpose": purposes[0] if purposes else None,
                "label_rank": item.get("order_index"),
                "matched_text": raw if raw and raw != name else None,
            }
        )

    # 핵심 성분끼리 실제로 걸린 관계만 — build_llm_input.py build_product_input()과 동일 로직.
    relations = []
    if key_ingredient_ids:
        rels = db.scalars(
            select(IngredientRelation).where(
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
        "product_name": "촬영한 제품",
        "brand": None,
        "category": None,
        # 스캔은 제품 카테고리를 알 수 없다 — 빈 문자열이면 프롬프트가 스킨케어 순서 언급을
        # 아예 하지 않는다(지어내지 않기 위한 의도된 동작, product_summary.md 참고).
        "category_description": "",
        "total_ingredient_count": len(raw_ingredients),
        "key_ingredients": key_ingredients_detail,
        "product_concern": [],
        "key_ingredient_relations": relations,
    }


def generate_scan_summary(db: Session, raw_ingredients: list[str]) -> dict | None:
    """OCR 원문 성분 목록으로 one_liner/composition_text를 실시간 생성한다.

    근거가 부족하거나(성분이 너무 적음/핵심 성분을 하나도 못 뽑음) LLM 호출·JSON 파싱이
    실패하면 None을 반환한다 — 호출부(라우터)가 이를 "요약 불가"로 취급해 프론트가 기존
    템플릿 문구를 그대로 쓰게 한다(에러로 화면을 막지 않는다).
    """
    cleaned = [r for r in raw_ingredients if r.strip()]
    if len(cleaned) < _MIN_INGREDIENTS_FOR_SUMMARY:
        return None

    input_data = _build_input(db, cleaned)
    if not input_data["key_ingredients"]:
        return None

    template = _PROMPT_PATH.read_text(encoding="utf-8")
    prompt = template.replace("{input_json}", json.dumps(input_data, ensure_ascii=False, indent=2))

    raw = _call_vllm(prompt)
    parsed = _extract_json(raw)
    if not parsed:
        return None

    return {
        "one_liner": parsed.get("one_liner") or "",
        "composition_text": parsed.get("composition_text") or "",
    }
