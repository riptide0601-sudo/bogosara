import re

import requests

from app.config import settings

TIMEOUT_SECONDS = 120

PROMPT_TEMPLATE = """아래는 화장품 성분/제품 관련 원본 설명이야.
사용자가 이해하기 쉽게 한두 문장으로 풀어서 다시 써줘.

[원본 설명]
{description}

출력 규칙:
- 원본에 없는 효능이나 효과를 추가하지 마
- '치료', '완치', '예방효과' 같은 의학적 표현 쓰지 마
- 원본에 없는 내용을 지어내지 마, 정보가 부족하면 있는 그대로만 풀어써
- 광고 문구처럼 과장하지 말고 담백하게 설명해
- 결과는 재구성된 문장만 출력해, 마크다운 서식이나 다른 부연설명 붙이지 마"""

PRODUCT_PROMPT_TEMPLATE = """아래는 화장품 "{product_name}"의 전성분 목록이야(농도 순).
이 성분 구성 전체를 종합해서 어떤 제품인지 한두 문장(2줄 이내)으로 설명해줘.

[전성분 목록]
{ingredient_list}

출력 규칙:
- 성분 목록에 없는 효능이나 효과를 지어내지 마
- '치료', '완치', '예방효과' 같은 의학적 표현 쓰지 마
- 특정 성분 몇 개만 보지 말고 전체 구성에서 두드러지는 특징 위주로 설명해
- 광고 문구처럼 과장하지 말고 담백하게 설명해
- 결과는 완성된 설명 문장만 출력해, 마크다운 서식이나 다른 부연설명 붙이지 마"""


def _strip_markdown(text: str) -> str:
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"[*_`#]", "", text)
    return text.strip()


def _generate(prompt: str) -> str:
    payload = {
        "model": settings.ollama_model,
        "prompt": prompt,
        "stream": False,
        "keep_alive": "30m",
        "options": {"num_predict": 200},
    }
    resp = requests.post(settings.ollama_url, json=payload, timeout=TIMEOUT_SECONDS)
    resp.raise_for_status()
    raw = resp.json().get("response", "")
    return _strip_markdown(raw)


def warm_up() -> None:
    """Load the model into memory ahead of the first real request."""
    payload = {
        "model": settings.ollama_model,
        "prompt": "ping",
        "stream": False,
        "keep_alive": "30m",
        "options": {"num_predict": 1},
    }
    resp = requests.post(settings.ollama_url, json=payload, timeout=TIMEOUT_SECONDS)
    resp.raise_for_status()


def rewrite_description(description: str) -> str:
    return _generate(PROMPT_TEMPLATE.format(description=description))


def summarize_product(product_name: str, ingredient_names: list[str]) -> str:
    ingredient_list = ", ".join(ingredient_names)
    return _generate(
        PRODUCT_PROMPT_TEMPLATE.format(product_name=product_name, ingredient_list=ingredient_list)
    )
