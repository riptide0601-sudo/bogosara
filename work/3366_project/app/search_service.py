"""제품 검색 — 제품명 / 브랜드 / 카테고리 3가지 필드만 검색 대상으로 한다.

[2026-08-21] 애초에 성분명·배합목적까지 포함한 통합검색으로 설계했었으나,
"성분을 검색해도 그 성분이 든 제품이 뜨는 건 원치 않는다"는 요구에 맞춰
검색 범위를 제품 자체의 표면 정보(이름/브랜드/카테고리)로만 좁혔다.

[2026-08-21 추가] "아누아 세럼"처럼 브랜드+카테고리(또는 이름의 일부)가 섞인
다중 단어 검색어도 매칭되게 했다. 검색어를 공백 기준으로 토큰화한 뒤, 각 토큰이
이름/브랜드/카테고리 중 어디에든 하나씩 있으면 그 제품을 결과에 포함한다(토큰 간
AND, 필드 간 OR). 예: "아누아 세럼" -> "아누아"는 브랜드에서, "세럼"은 이름 또는
카테고리에서 각각 찾아서 둘 다 있으면 매칭. 순서나 붙어있는지는 안 따진다.

참고: product.category는 현재 데이터의 상당수가 NULL이다(111개 중 세럼/에센스/앰플,
스킨/토너, 기타 3종류만 채워져 있고 나머지는 비어있음). 카테고리 검색 자체는
정상 동작하지만, 카테고리가 비어있는 제품은 카테고리 토큰으로는 안 걸린다는 점을
프론트 안내 문구에 반영하는 게 좋다.
"""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.product import Product


@dataclass
class SearchResultItem:
    product_id: str
    product_name: str
    brand: str | None
    category: str | None
    score: float  # 랭킹용 내부 점수 (프론트에 노출 안 해도 됨, 정렬용)


# 랭킹 가중치 — 이름 완전일치(전체 검색어 기준) > 토큰별 이름/브랜드/카테고리 부분일치
_WEIGHT_NAME_EXACT = 100
_WEIGHT_TOKEN_NAME = 40
_WEIGHT_TOKEN_BRAND = 35
_WEIGHT_TOKEN_CATEGORY = 20


def _tokenize(query: str) -> list[str]:
    return [t for t in query.strip().lower().split() if t]


def search_products(query: str, db: Session, limit: int = 30) -> list[SearchResultItem]:
    """제품명·브랜드·카테고리에서 검색한다 (성분/배합목적 검색 없음).

    검색어는 공백 기준으로 토큰화해서, 모든 토큰이 (이름/브랜드/카테고리 중
    아무 데나) 각각 한 번씩은 매칭돼야 결과에 포함시킨다 (토큰 간 AND).
    """
    tokens = _tokenize(query)
    if not tokens:
        return []

    # DB 레벨에서 1차로 후보를 좁히기보다, 제품 수가 많지 않으니 애플리케이션
    # 레벨에서 전체를 훑는다. 제품이 수만 건으로 늘어나면 각 토큰마다 ILIKE
    # 조건을 만들어 DB 레벨 AND 필터로 전환하는 걸 권장.
    all_products = db.scalars(select(Product)).all()

    results = []
    for p in all_products:
        name = (p.product_name or "").lower()
        brand = (p.brand or "").lower()
        category = (p.category or "").lower()

        score = 0.0
        all_tokens_matched = True
        for tok in tokens:
            in_name = tok in name
            in_brand = tok in brand
            in_category = tok in category
            if not (in_name or in_brand or in_category):
                all_tokens_matched = False
                break
            if in_name:
                score += _WEIGHT_TOKEN_NAME
            if in_brand:
                score += _WEIGHT_TOKEN_BRAND
            if in_category:
                score += _WEIGHT_TOKEN_CATEGORY

        if not all_tokens_matched:
            continue

        full_query = query.strip().lower()
        if name == full_query:
            score += _WEIGHT_NAME_EXACT

        results.append(
            SearchResultItem(
                product_id=p.product_id,
                product_name=p.product_name,
                brand=p.brand,
                category=p.category,
                score=score,
            )
        )

    results.sort(key=lambda r: (-r.score, r.product_name))
    return results[:limit]
