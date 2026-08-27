from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ProductFamilyMember(Base):
    """어떤 제품을 어떤 성분 계열의 "비교 대상"으로 칠지 사람이 직접 정한 목록.

    ingredient_family_member(성분명 키워드 매칭)만으로 비교 모수를 정하면 DB 전체
    제품(현재 히알루론산 계열 209개) 중 극미량만 들어있는 제품까지 다 섞여 비교가
    무의미해진다. 그래서 실제 순위 비교는 이 표에 큐레이션된 제품끼리만 하고,
    ingredient_family_member는 "그 제품 안에서 어떤 성분이 대표 성분인지" 찾는
    용도로만 계속 쓴다 (app/routers/products.py get_product_family_rank 참고).
    """

    __tablename__ = "product_family_member"

    family_id: Mapped[int] = mapped_column(
        ForeignKey("ingredient_family.family_id"), primary_key=True
    )
    product_id: Mapped[str] = mapped_column(
        String, ForeignKey("product.product_id"), primary_key=True
    )

    family: Mapped["IngredientFamily"] = relationship()
    product: Mapped["Product"] = relationship()
