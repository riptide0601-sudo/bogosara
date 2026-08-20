from pydantic import BaseModel

from app.schemas.ingredient import IngredientDetail


class OcrIngredientResult(BaseModel):
    label_rank: int
    matched_text: str
    ingredient: IngredientDetail | None = None


class OcrAnalyzeResponse(BaseModel):
    engine: str
    raw_ingredients: list[str]
    results: list[OcrIngredientResult]
