"""제품명 키워드로 화장품 카테고리를 추정하고, 카테고리별 사용 순서·설명 문구를 제공합니다.

classify()는 product 생성/백필 시 product_name으로부터 카테고리를 판정할 때 쓰고,
그 결과(카테고리 이름 문자열)는 product.category 컬럼에 저장해 검색 필터링에 쓴다.
get_info()는 이미 저장된 category 값에서 순서·설명 문구를 다시 찾아올 때 쓴다 — 매번
product_name을 재분류하지 않고 저장된 값을 기준으로 하기 위함이다.

카테고리는 스킨케어 루틴 순서(스킨/토너 -> 세럼·에센스·앰플 -> 크림)를 그대로 반영하고,
어디에도 안 걸리면 "기타"로 분류한다.

키워드 검사 순서에 주의: "스킨"은 "스킨1004"처럼 브랜드명에도 흔히 들어가서, 세럼/에센스/
앰플·크림처럼 더 명확한 키워드를 먼저 확인한 뒤 스킨/토너는 맨 마지막에 확인한다.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ProductCategoryInfo:
    name: str
    order: int
    description: str


TONER = ProductCategoryInfo(
    name="스킨/토너",
    order=1,
    description="해당 제품은 피부결을 정돈하고 다음 단계 제품의 흡수를 돕는 역할을 하므로, 세안 후 가장 먼저 사용하시면 됩니다.",
)
SERUM = ProductCategoryInfo(
    name="세럼/에센스/앰플",
    order=2,
    description="해당 제품은 영양분을 공급하므로 가벼운 스킨(토너) 후에 사용하시면 됩니다.",
)
CREAM = ProductCategoryInfo(
    name="크림",
    order=3,
    description="해당 제품은 유수분을 채우고 보호막을 형성하므로, 스킨케어 마지막 단계에서 사용하시면 됩니다.",
)
OTHER = ProductCategoryInfo(name="기타", order=99, description="")

ALL_CATEGORIES = [TONER, SERUM, CREAM, OTHER]
_BY_NAME = {category.name: category for category in ALL_CATEGORIES}

# (키워드 목록, 카테고리) 순서대로 검사한다 — 헷갈릴 위험이 적은 키워드부터.
_RULES: list[tuple[list[str], ProductCategoryInfo]] = [
    (["세럼", "에센스", "앰플"], SERUM),
    (["크림"], CREAM),
    (["토너", "스킨"], TONER),
]


def classify(product_name: str) -> ProductCategoryInfo:
    for keywords, category in _RULES:
        if any(keyword in product_name for keyword in keywords):
            return category
    return OTHER


def get_info(category_name: str | None) -> ProductCategoryInfo:
    return _BY_NAME.get(category_name, OTHER)
