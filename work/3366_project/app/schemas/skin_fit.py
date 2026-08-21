from pydantic import BaseModel


class SkinFitBreakdownItem(BaseModel):
    ingredient_id: int
    name_kr: str | None = None
    score: int
    function: str | None = None
    caution: str | None = None


class SkinFitRead(BaseModel):
    skin_type: str
    fit_score: float
    raw_score: int
    matched_count: int
    total_ingredient_count: int
    breakdown: list[SkinFitBreakdownItem] = []
