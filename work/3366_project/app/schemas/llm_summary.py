from datetime import datetime

from pydantic import BaseModel, ConfigDict


class LLMSummaryBase(BaseModel):
    summary_text: str | None = None
    benefit_text: str | None = None
    caution_text: str | None = None
    usage_reason_text: str | None = None
    caution_group_text: str | None = None
    combo_recommendation: str | None = None


class LLMSummaryUpsert(LLMSummaryBase):
    pass


class LLMSummaryRead(LLMSummaryBase):
    model_config = ConfigDict(from_attributes=True)

    ingredient_id: int
    summary_generated_at: datetime | None = None
