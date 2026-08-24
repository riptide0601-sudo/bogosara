"""전성분표 원문(엑셀 등 자유 텍스트)을 성분 토큰 리스트로 분리하는 공통 파서.

엑셀마다 구분자가 다를 수 있어(쉼표 "," 또는 골뱅이 "@") 어느 쪽이 더 많이 쓰였는지
보고 자동 감지한다. 괄호 안의 구분자는 무시하고(예: "나이아신아마이드(30,000 ppm)"),
"[라벨] 정제수, ..."/"PDRN 앰플 30ml: 정제수,..." 같은 접두 라벨과, 성분 뒤에 붙는
"*"/"※" 표시·각주("... * 피디알엔: 소듐디엔에이", "리모넨※ ※ 자연유래...")는 제거한다.
"""

import re

_BRACKET_PREFIX = re.compile(r"^\[[^\]]*\]\s*")
_TRAILING_PAREN = re.compile(r"\([^()]*\)\s*$")
_FOOTNOTE_MARK = re.compile(r"[*※].*$")


def detect_delimiter(text: str) -> str:
    return "@" if text.count("@") > text.count(",") else ","


def _strip_label_prefix(text: str, delimiter: str) -> str:
    match = _BRACKET_PREFIX.match(text)
    if match:
        return text[match.end():]

    colon_idx = text.find(":")
    delim_idx = text.find(delimiter)
    if colon_idx != -1 and colon_idx < 40 and (delim_idx == -1 or colon_idx < delim_idx):
        return text[colon_idx + 1 :]
    return text


def _split_ingredients(text: str, delimiter: str) -> list[str]:
    tokens: list[str] = []
    current: list[str] = []
    depth = 0
    for ch in text:
        if ch == "(":
            depth += 1
            current.append(ch)
        elif ch == ")":
            depth = max(0, depth - 1)
            current.append(ch)
        elif ch == delimiter and depth == 0:
            tokens.append("".join(current))
            current = []
        else:
            current.append(ch)
    if current:
        tokens.append("".join(current))
    return [t.strip() for t in tokens if t.strip()]


def parse_ingredient_tokens(raw_text: str) -> list[str]:
    """전성분 원문을 (라벨 접두·각주·"*"/"※" 표시 제거된) 성분 토큰 리스트로 분리합니다."""
    text = (raw_text or "").strip().lstrip("\t").strip()
    if not text:
        return []
    delimiter = detect_delimiter(text)
    text = _strip_label_prefix(text, delimiter)
    tokens = _split_ingredients(text, delimiter)
    cleaned = [_FOOTNOTE_MARK.sub("", t).strip() for t in tokens]
    return [t for t in cleaned if t]


def clean_for_matching(token: str) -> str:
    """매칭용으로 끝에 붙은 농도 표기(예: "(29,049ppm)")를 제거한 이름."""
    return _TRAILING_PAREN.sub("", token).strip()
