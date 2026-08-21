"""자유 텍스트(OCR 원문, 엑셀 성분표 등)를 ingredient 테이블과 매칭하는 공통 로직.

OCR 분석(app/routers/ocr.py)과 엑셀 일괄 임포트(scripts/*) 등, "성분명일 수도 있는
텍스트 토큰 하나를 표준 성분과 매칭해야 하는" 여러 곳에서 공유한다.
"""

from sqlalchemy import func, literal, select
from sqlalchemy.orm import Session

from app.models.ingredient import Ingredient
from app.routers.ingredients import search_ingredient_ids

_MIN_EMBEDDED_NAME_LEN = 4
_MAX_EMBEDDED_MATCHES = 5


def find_embedded_ingredient_ids(token: str, db: Session) -> list[int]:
    """토큰 전체가 아니라, 토큰 안에 파묻혀 있는 성분명들을 모두 찾아냅니다.

    쉼표 없이 이웃 성분·문구와 통째로 합쳐진 토큰(예: "시트릭애씨드라피노오스 아데노신"
    안에 실은 2~3개 성분이 섞여 있음)을 구제하기 위한 마지막 폴백입니다. 후보 이름들을
    모두 모은 뒤, 긴 이름부터 그리디하게 겹치지 않는 구간을 채택해 하나의 블록에서
    여러 성분을 복원합니다. (짧은 이름은 우연히 걸릴 오탐 위험이 커서 4자 미만은 제외)
    """
    stmt = select(Ingredient.ingredient_id, Ingredient.name_kr).where(
        Ingredient.name_kr.isnot(None),
        func.length(Ingredient.name_kr) >= _MIN_EMBEDDED_NAME_LEN,
        literal(token).like(func.concat("%", Ingredient.name_kr, "%")),
    )
    candidates = db.execute(stmt).all()
    if not candidates:
        return []

    spans = []
    for ingredient_id, name_kr in candidates:
        start = token.find(name_kr)
        if start != -1:
            spans.append((start, start + len(name_kr), ingredient_id))
    spans.sort(key=lambda span: span[1] - span[0], reverse=True)

    chosen: list[tuple[int, int, int]] = []
    for start, end, ingredient_id in spans:
        if any(start < c_end and end > c_start for c_start, c_end, _ in chosen):
            continue
        chosen.append((start, end, ingredient_id))
        if len(chosen) >= _MAX_EMBEDDED_MATCHES:
            break

    chosen.sort(key=lambda c: c[0])
    return [ingredient_id for _, _, ingredient_id in chosen]


def match_ingredient_ids(token: str, db: Session) -> list[int]:
    """텍스트 토큰 하나를 ingredient 테이블과 매칭해 ingredient_id 목록을 반환합니다.

    보통은 토큰 하나 = 성분 하나라 결과가 최대 1개지만, 쉼표 없이 여러 성분이
    통째로 합쳐진 토큰이라면 여러 개가 나올 수 있습니다.

    1) 검색창(GET /ingredients?query=)과 동일한 알고리즘(search_ingredient_ids) —
       substring 매칭 우선, 없으면 자모 기반 fuzzy 매칭으로 폴백
    2) 그래도 실패하면 토큰 안에 성분명이 파묻혀 있는지 마지막으로 확인
    """
    token = token.strip()
    if not token:
        return []

    ids = search_ingredient_ids(token, db)
    if ids:
        return [ids[0]]

    return find_embedded_ingredient_ids(token, db)
