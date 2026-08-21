from datetime import datetime
from urllib.parse import quote

from pydantic import BaseModel, ConfigDict, computed_field

from app.product_category import get_info as get_category_info
from app.schemas.ingredient import IngredientDetail

_OLIVEYOUNG_SEARCH_URL = "https://www.oliveyoung.co.kr/store/search/getSearchMain.do?query={query}"


class ProductBase(BaseModel):
    product_name: str
    brand: str | None = None
    summary: str | None = None


class ProductCreate(ProductBase):
    pass


class ProductRead(ProductBase):
    model_config = ConfigDict(from_attributes=True)

    product_id: str
    category: str | None = None
    summary_generated_at: datetime | None = None

    @computed_field
    @property
    def oliveyoung_url(self) -> str:
        # 올리브영에 등록된 상품별 직접 링크(고유 goodsNo)를 DB에 갖고 있지 않아서,
        # 제품명으로 올리브영 검색 결과 페이지를 가리키는 URL을 그때그때 만들어 준다.
        return _OLIVEYOUNG_SEARCH_URL.format(query=quote(self.product_name))

    @computed_field
    @property
    def category_order(self) -> int:
        # 스킨케어 루틴 순서: 스킨/토너(1) -> 세럼/에센스/앰플(2) -> 크림(3) -> 기타(99)
        return get_category_info(self.category).order

    @computed_field
    @property
    def category_description(self) -> str:
        return get_category_info(self.category).description


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
