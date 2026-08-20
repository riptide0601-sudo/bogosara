from pydantic import BaseModel, ConfigDict

from app.schemas.ingredient import IngredientRead


class IngredientRelationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    relation_id: int
    relation_type: str
    user_message: str | None = None
    related_ingredient: IngredientRead
