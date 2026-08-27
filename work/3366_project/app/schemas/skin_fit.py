from pydantic import BaseModel


class RiskIngredientRead(BaseModel):
    ingredient_id: int
    name_kr: str | None = None
    risk_type: str | None = None
    reason: str | None = None
    source: str | None = None


class SkinRiskRead(BaseModel):
    skin_type: str
    has_risk: bool
    risk_ingredients: list[RiskIngredientRead] = []
    total_ingredient_count: int


class SkinTypeCountRead(BaseModel):
    skin_type: str
    good_count: int
    caution_count: int
