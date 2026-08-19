import re

import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "gemma2:2b"
TIMEOUT_SECONDS = 120

# 출력에 섞이면 안 되는 표현 (의학적 효능 단정 표현)
BANNED_PHRASES = ["치료", "완치", "예방효과", "100% 안전", "부작용 없음"]

PROMPT_TEMPLATE = """너는 화장품 "성분"에 대한 정보를 사용자가 이해하기 쉽게 풀어주는 역할이야.
아래는 특정 제품이 아니라 화장품에 일반적으로 쓰이는 "성분" 자체에 대한 정보야.

[성분명]
{ingredient_name}

[배합목적 - 이 성분이 화장품에 들어가는 이유/역할]
{purpose}

[성분 정의 원문]
{description}

이 정보를 바탕으로 이 "성분"이 화장품에서 어떤 역할을 하는지
한두 문장으로 쉽게 풀어서 설명해줘.

출력 규칙 (반드시 지켜):
1. "이 화장품은", "이 제품은" 같은 특정 제품을 지칭하는 표현을 쓰지 마.
   반드시 "이 성분은" 또는 "{ingredient_name}은/는" 으로 문장을 시작해.
2. 위에 주어진 [배합목적]과 [성분 정의 원문]에 없는 효능·효과는
   절대 추가하지 마. 짐작하거나 지어내지 마.
3. 정의 원문이 비어 있거나 부실하면, 배합목적만 가지고 "~하는 역할을
   하는 성분입니다" 수준으로 담백하게만 설명해. 없는 정보를 채우지 마.
4. "치료", "완치", "예방효과", "100% 안전", "부작용 없음" 같은
   의학적/단정적 표현은 절대 쓰지 마.
5. 광고 문구처럼 과장하지 말고 사전적으로 담백하게 설명해.
6. 결과는 재구성된 설명 문장만 출력해. 마크다운 서식(**, #, - 등)이나
   "네, 알겠습니다" 같은 부연설명은 절대 붙이지 마."""


def _strip_markdown(text: str) -> str:
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"[*_`#]", "", text)
    return text.strip()


def _contains_banned_phrase(text: str) -> str | None:
    for phrase in BANNED_PHRASES:
        if phrase in text:
            return phrase
    return None


def rewrite_description(
    ingredient_name: str,
    description: str | None,
    purpose: str | None,
) -> str:
    """
    성분명 + 배합목적 + 정의 원문을 받아 이해하기 쉬운 설명으로 재구성.
    정의 원문이 없으면 배합목적만으로 담백하게 생성하도록 프롬프트에서 유도.
    """
    payload = {
        "model": MODEL_NAME,
        "prompt": PROMPT_TEMPLATE.format(
            ingredient_name=ingredient_name,
            description=description or "정보 없음",
            purpose=purpose or "정보 없음",
        ),
        "stream": False,
        "options": {"temperature": 0.3},  # 재구성 목적이므로 창작성 낮게
    }
    resp = requests.post(OLLAMA_URL, json=payload, timeout=TIMEOUT_SECONDS)
    resp.raise_for_status()
    raw = resp.json().get("response", "")
    result = _strip_markdown(raw)

    banned = _contains_banned_phrase(result)
    if banned:
        # 검증 실패 시 정책: 일단 예외 발생 (상위에서 원본 description으로 폴백 처리 권장)
        raise ValueError(f"LLM 출력에 금지 표현 포함: '{banned}'")

    return result