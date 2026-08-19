import re

import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "gemma2:2b"
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


def _strip_markdown(text: str) -> str:
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"[*_`#]", "", text)
    return text.strip()


def rewrite_description(description: str) -> str:
    payload = {
        "model": MODEL_NAME,
        "prompt": PROMPT_TEMPLATE.format(description=description),
        "stream": False,
    }
    resp = requests.post(OLLAMA_URL, json=payload, timeout=TIMEOUT_SECONDS)
    resp.raise_for_status()
    raw = resp.json().get("response", "")
    return _strip_markdown(raw)
