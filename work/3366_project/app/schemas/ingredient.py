from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.llm_summary import LLMSummaryRead
from app.schemas.purpose import PurposeRead


class IngredientBase(BaseModel):
    name_kr: str | None = None
    name_en: str | None = None
    synonyms: list[str] | None = None
    safety_level: str | None = None
    summary: str | None = None


class IngredientCreate(IngredientBase):
    pass


class IngredientUpdate(BaseModel):
    name_kr: str | None = None
    name_en: str | None = None
    synonyms: list[str] | None = None
    safety_level: str | None = None
    summary: str | None = None


class IngredientRead(IngredientBase):
    model_config = ConfigDict(from_attributes=True)

    ingredient_id: int
    summary_generated_at: datetime | None = None


class IngredientDetail(IngredientRead):
    purposes: list[PurposeRead] = []
    llm_summary: LLMSummaryRead | None = None
