from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.ingredient import IngredientDetail


class ProductBase(BaseModel):
    product_name: str
    brand: str | None = None
    summary: str | None = None


class ProductCreate(ProductBase):
    pass


class ProductRead(ProductBase):
    model_config = ConfigDict(from_attributes=True)

    product_id: str
    summary_generated_at: datetime | None = None


class ProductIngredientLink(BaseModel):
    ingredient_id: int
    label_rank: int | None = None
    matched_text: str | None = None


class ProductIngredientDetail(BaseModel):
    label_rank: int | None = None
    matched_text: str | None = None
    ingredient: IngredientDetail

    model_config = ConfigDict(from_attributes=True)


class ProductSimilarityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    product: ProductRead
    score: float


class ProductDetail(ProductRead):
    ingredients: list[ProductIngredientDetail] = []
    key_ingredients: list[ProductIngredientDetail] = []
    similar_products: list[ProductSimilarityRead] = []
