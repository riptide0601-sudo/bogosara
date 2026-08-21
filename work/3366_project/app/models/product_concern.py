from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ProductConcern(Base):
    """제품이 어떤 피부 고민(수분/진정/미백/모공 등)을 겨냥하는지 나타내는 태그.

    ingredient_purpose와 달리 성분이 아니라 제품 단위로 큐레이션된 정보라 별도
    테이블로 둔다. 제품 하나가 여러 고민에 걸릴 수 있어 (product_id, concern) 복합키.
    """

    __tablename__ = "product_concern"

    product_id: Mapped[str] = mapped_column(
        String, ForeignKey("product.product_id"), primary_key=True
    )
    concern: Mapped[str] = mapped_column(String, primary_key=True)

    product: Mapped["Product"] = relationship(back_populates="product_concerns")
