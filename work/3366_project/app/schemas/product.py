import json
from datetime import datetime
from urllib.parse import quote

from pydantic import BaseModel, ConfigDict, computed_field, field_validator

from app.product_category import get_info as get_category_info
from app.schemas.ingredient import IngredientDetail
from app.schemas.ingredient_relation import IngredientRelationRead
from app.schemas.marketing_family import MatchedFamily
from app.schemas.purpose_count import PurposeCount
from app.schemas.skin_fit import SkinTypeCountRead

_OLIVEYOUNG_SEARCH_URL = "https://www.oliveyoung.co.kr/store/search/getSearchMain.do?query={query}"


class ProductBase(BaseModel):
    product_name: str
    brand: str | None = None
    summary: str | None = None
    composition_text: str | None = None
    image_url: str | None = None


class ProductCreate(ProductBase):
    pass


class ProductRead(ProductBase):
    model_config = ConfigDict(from_attributes=True)

    product_id: str
    category: str | None = None
    summary_generated_at: datetime | None = None
    # ingredient_skin_score 매칭 요약 (예: "지성에 좋은 성분 2개, 건성에 유의해야할 성분 1개
    # 있습니다."). 매칭 없으면 "...". _to_detail/list_products에서 계산해 채워 넣는다
    # (모델 속성이 아니라 응답 시점에 조립하는 값이라 기본값은 항상 "...").
    skin_score_summary: str = "..."
    # app.core_ingredient_selector가 뽑아 scripts/backfill_key_ingredients.py로 채운 값.
    # DB엔 JSON 배열 문자열로 저장돼 있어서(product.key_ingredients/key_purposes) 아래
    # validator가 파싱해서 리스트로 내려준다. 아직 안 채워진 제품은 빈 리스트.
    key_ingredients: list[str] = []
    key_purposes: list[str] = []

    @field_validator("key_ingredients", "key_purposes", mode="before")
    @classmethod
    def _parse_json_list(cls, value: object) -> object:
        if value is None:
            return []
        if isinstance(value, str):
            return json.loads(value)
        return value

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
    # 이 성분이 제품 내 다른 성분과 이루는 시너지/악화 관계 (app/models/ingredient_relation.py).
    # 상대 성분이 같은 제품에 들어있는지 여부와 무관하게, 이 성분에 걸린 관계를 전부 담는다.
    relations: list[IngredientRelationRead] = []

    model_config = ConfigDict(from_attributes=True)


class ProductSimilarityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    product: ProductRead
    score: float


class ProductDetail(ProductRead):
    ingredients: list[ProductIngredientDetail] = []
    # "key_ingredients"가 아니라 "top_ingredients"인 이유: Product ORM 모델에 이미
    # key_ingredients(TEXT, core_ingredient_selector가 뽑은 성분명 JSON 문자열) 컬럼이
    # 있어서, 같은 이름을 쓰면 model_validate(product)가 이 필드를 그 문자열로 채우려다
    # list[ProductIngredientDetail] 타입 검증에 실패한다. 이 필드는 별개로, label_rank
    # 상위 DEFAULT_TOP_K개를 그대로 슬라이스한 성분 객체 목록이다 (_to_detail 참고).
    top_ingredients: list[ProductIngredientDetail] = []
    similar_products: list[ProductSimilarityRead] = []
    # "상품명 성분, 진짜 들어있나요?" 계열 묶음 블록 (app/marketing_families.py 참고).
    # 근거(ingredient_family/ingredient_family_member)가 아직 지정 10개 상품 기준이라,
    # 대상 밖 제품은 항상 빈 리스트.
    ingredient_families: list[MatchedFamily] = []
    # "이 성분들, 무슨 일을 하나요?" 배합목적 카운트 카드 (app/purpose_counts.py 참고).
    # 지정 상품 제한 없이 DB 전체 제품에 적용된다.
    purpose_counts: list[PurposeCount] = []
    # "피부 타입별 참고" 막대바용 구조화 데이터 (app/skin_fit.py compute_skin_type_counts).
    # skin_score_summary(문장)와 같은 근거, 막대바 렌더링에 쓰는 숫자 버전.
    skin_type_counts: list[SkinTypeCountRead] = []
