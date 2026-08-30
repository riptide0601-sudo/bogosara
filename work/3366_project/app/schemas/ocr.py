from pydantic import BaseModel

from app.schemas.ingredient import IngredientDetail
from app.schemas.ingredient_family import FamilyRankRead
from app.schemas.marketing_family import MatchedFamily
from app.schemas.product import ProductSimilarityRead
from app.schemas.skin_fit import SkinRiskRead, SkinTypeCountRead


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


class OcrCompositionIngredientInput(BaseModel):
    """/ocr/analyze의 results[] 중 DB에 실제 매칭된 것만(ingredient가 null이 아닌 것) 골라
    그대로 되돌려보낸다 — 성분 계열/순위/피부타입 섹션은 전부 DB ingredient_id가 있어야
    계산할 수 있어서, 매칭 안 된 원문 토큰은 애초에 이 목록에 들어올 필요가 없다."""

    ingredient_id: int
    label_rank: int
    matched_text: str | None = None


class OcrCompositionRequest(BaseModel):
    # 핵심 성분 큐레이션에 필요 — /ocr/summarize와 동일한 입력(app/ocr_summary.py
    # get_key_ingredients 참고).
    raw_ingredients: list[str]
    matched: list[OcrCompositionIngredientInput]


class OcrCompositionResponse(BaseModel):
    ingredient_families: list[MatchedFamily] = []
    family_ranks: list[FamilyRankRead] = []
    skin_type_counts: list[SkinTypeCountRead] = []
    skin_risks: list[SkinRiskRead] = []
    # 검색 흐름의 product.key_ingredients(core_ingredient_selector 큐레이션, order_index순
    # 상위 5개 안팎)와 동일한 이름 배열 — 프론트가 이걸로 "핵심 성분" 카드를 채운다.
    key_ingredients: list[str] = []
    # 검색 흐름의 product.similar_products와 동일한 응답 모양(app/similarity.py
    # find_similar_products_for_ingredients) — "이런 제품은 어때요?" 추천용, score 내림차순.
    similar_products: list[ProductSimilarityRead] = []
