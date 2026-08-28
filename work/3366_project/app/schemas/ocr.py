from pydantic import BaseModel

from app.schemas.ingredient import IngredientDetail


class OcrIngredientResult(BaseModel):
    label_rank: int
    matched_text: str
    ingredient: IngredientDetail | None = None


class OcrTextRegion(BaseModel):
    """OCR이 사진에서 인식한 줄 하나 — 성분 요약 페이지가 사진 위에 형광펜으로 표시하는 데
    쓴다(predict_module.py의 paddleocr 경로에서만 채워짐, 다른 엔진은 항상 빈 리스트)."""

    text: str
    # [x1, y1, x2, y2] — 이미지 너비/높이 기준 0~1 비율(픽셀 아님). 프론트가 사진을 표시하는
    # 크기에 그대로 곱하면 위치가 나온다.
    box_pct: list[float]


class OcrAnalyzeResponse(BaseModel):
    engine: str
    raw_ingredients: list[str]
    results: list[OcrIngredientResult]
    text_regions: list[OcrTextRegion] = []


class OcrSummarizeRequest(BaseModel):
    """POST /ocr/summarize 입력 — /ocr/analyze가 이미 돌려준 raw_ingredients를 그대로
    되돌려보낸다(OCR을 다시 돌리지 않는다, app/ocr_summary.py 참고)."""

    raw_ingredients: list[str]


class OcrSummarizeResponse(BaseModel):
    one_liner: str
    composition_text: str
