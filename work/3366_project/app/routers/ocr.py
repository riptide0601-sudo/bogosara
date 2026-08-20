import base64
import sys
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import func, literal, select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.ingredient import Ingredient
from app.routers.ingredients import _detail_query, _to_detail, search_ingredient_ids
from app.schemas.ocr import OcrAnalyzeResponse, OcrIngredientResult

# src/core (OCR 모듈)는 이 백엔드와 별도 폴더에 있는 형제 프로젝트라 sys.path에 추가해야 import된다.
_OCR_CORE_DIR = Path(__file__).resolve().parents[4] / "src" / "core"
if str(_OCR_CORE_DIR) not in sys.path:
    sys.path.insert(0, str(_OCR_CORE_DIR))

from predict_module import predict as ocr_predict  # noqa: E402

router = APIRouter(prefix="/ocr", tags=["ocr"])


_MIN_EMBEDDED_NAME_LEN = 4
_MAX_EMBEDDED_MATCHES = 5


def _find_embedded_ingredient_ids(token: str, db: Session) -> list[int]:
    """토큰 전체가 아니라, 토큰 안에 파묻혀 있는 성분명들을 모두 찾아냅니다.

    라벨 원문에 쉼표가 없는 지점(문장 경계, 줄바꿈 등)에서 이웃 성분·문구와 통째로
    합쳐진 토큰(예: "시트릭애씨드라피노오스 아데노신" 안에 실은 2~3개 성분이 섞여 있음)을
    구제하기 위한 마지막 폴백입니다. 후보 이름들을 모두 모은 뒤, 긴 이름부터
    그리디하게 겹치지 않는 구간을 채택해 하나의 블록에서 여러 성분을 복원합니다.
    (짧은 이름은 우연히 걸릴 오탐 위험이 커서 4자 미만은 제외)
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


def _match_ingredient_ids(token: str, db: Session) -> list[int]:
    """OCR 토큰 하나를 ingredient 테이블과 매칭해 ingredient_id 목록을 반환합니다.

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

    return _find_embedded_ingredient_ids(token, db)


@router.post("/analyze", response_model=OcrAnalyzeResponse)
async def analyze_label(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """라벨 사진을 업로드받아 OCR로 성분을 추출하고, DB의 표준 성분과 매칭해 반환합니다."""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=422, detail="이미지 파일만 업로드할 수 있습니다.")

    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=422, detail="빈 파일입니다.")

    image_b64 = base64.b64encode(image_bytes).decode("ascii")
    engine = settings.ocr_engine

    result = ocr_predict(
        message={"image_base64": image_b64, "engine": engine},
        uuid_id=uuid.uuid4().hex,
    )
    if result["status"] != 200:
        raise HTTPException(status_code=502, detail=result["message"])

    tokens = result["data"]["ingredients"]

    # rank, 원본 토큰, 매칭된 ingredient_id 목록(없으면 빈 리스트) 을 먼저 모두 계산한다.
    matches: list[tuple[int, str, list[int]]] = [
        (rank, token, _match_ingredient_ids(token, db)) for rank, token in enumerate(tokens)
    ]

    unique_ids = {mid for _, _, ids in matches for mid in ids}
    ingredients_by_id = {
        ingredient.ingredient_id: _to_detail(ingredient)
        for ingredient in db.scalars(
            _detail_query().where(Ingredient.ingredient_id.in_(unique_ids))
        ).all()
    }

    results: list[OcrIngredientResult] = []
    for rank, token, ids in matches:
        if not ids:
            results.append(OcrIngredientResult(label_rank=rank, matched_text=token, ingredient=None))
            continue
        for matched_id in ids:
            ingredient = ingredients_by_id.get(matched_id)
            # 하나의 토큰에서 여러 성분을 복원한 경우, 원본(뒤섞인) 텍스트 대신
            # 실제로 인식된 성분명을 matched_text로 보여준다.
            matched_text = ingredient.name_kr or ingredient.name_en or token if len(ids) > 1 else token
            results.append(
                OcrIngredientResult(label_rank=rank, matched_text=matched_text, ingredient=ingredient)
            )

    return OcrAnalyzeResponse(engine=engine, raw_ingredients=tokens, results=results)
