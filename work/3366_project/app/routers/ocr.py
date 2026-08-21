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
from app.routers.ingredients import _detail_query, _to_detail
from app.schemas.ocr import OcrAnalyzeResponse, OcrIngredientResult

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
