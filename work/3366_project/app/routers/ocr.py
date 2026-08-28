import base64
import sys
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.ingredient_matching import match_ingredient_ids
from app.models.ingredient import Ingredient
from app.ocr_summary import generate_scan_summary
from app.routers.ingredients import _detail_query, _to_detail
from app.schemas.ocr import (
    OcrAnalyzeResponse,
    OcrIngredientResult,
    OcrSummarizeRequest,
    OcrSummarizeResponse,
    OcrTextRegion,
)

# src/core (OCR 모듈)는 이 백엔드와 별도 폴더에 있는 형제 프로젝트라 sys.path에 추가해야 import된다.
_OCR_CORE_DIR = Path(__file__).resolve().parents[4] / "src" / "core"
if str(_OCR_CORE_DIR) not in sys.path:
    sys.path.insert(0, str(_OCR_CORE_DIR))

from predict_module import predict as ocr_predict  # noqa: E402

router = APIRouter(prefix="/ocr", tags=["ocr"])


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
        (rank, token, match_ingredient_ids(token, db)) for rank, token in enumerate(tokens)
    ]

    # 사진 위 형광펜 표시는 "OCR이 뭔가 글자를 읽은 줄"이 아니라 "그중 실제로 성분으로
    # 인식(=DB 매칭)된 줄"만 보여준다 — 안 그러면 라벨의 마케팅 문구·사용법 줄까지 같이
    # 하이라이트돼서 "여기가 전성분이다"라는 의미가 흐려진다. 한 줄에 성분이 여러 개
    # 쉼표로 묶여 있어도(예: "정제수, 글리세린") 그중 하나라도 매칭됐으면 그 줄 전체를
    # 표시한다 — 줄 단위 하이라이트라는 기존 범위는 그대로 유지.
    matched_token_texts = {token for _, token, ids in matches if ids}
    text_regions = [
        OcrTextRegion(text=region["text"], box_pct=region["box_pct"])
        for region in result["data"].get("text_regions", [])
        if any(matched in region["text"] for matched in matched_token_texts)
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

    return OcrAnalyzeResponse(
        engine=engine, raw_ingredients=tokens, results=results, text_regions=text_regions
    )


@router.post("/summarize", response_model=OcrSummarizeResponse)
async def summarize_scan(payload: OcrSummarizeRequest, db: Session = Depends(get_db)):
    """스캔 결과 화면의 한줄요약/성분구성 설명 — 검색 흐름과 달리 등록된 Product가 없어
    미리 캐싱된 값이 없다. /ocr/analyze가 이미 돌려준 raw_ingredients로 그 자리에서
    LLM(Qwen/vLLM)을 호출한다(app/ocr_summary.py). 프론트는 결과 화면 진입 후 이 엔드포인트를
    비동기로 호출해 헤드라인/성분구성 섹션을 나중에 채워 넣는다 — OCR 인식 자체를 이 호출 때문에
    더 기다리게 하지 않기 위해서다."""
    summary = generate_scan_summary(db, payload.raw_ingredients)
    if summary is None:
        raise HTTPException(status_code=422, detail="요약을 생성할 근거가 부족합니다.")
    return OcrSummarizeResponse(**summary)
