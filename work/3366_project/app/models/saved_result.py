from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SavedResult(Base):
    """마이페이지 "저장한 결과" — 유저가 제품 상세를 북마크한 기록.
    (user_id, product_id) 복합키라 같은 제품을 다시 저장해도 새 행이 생기지 않는다."""

    __tablename__ = "saved_result"

    user_id: Mapped[str] = mapped_column(String, ForeignKey("app_user.user_id"), primary_key=True)
    product_id: Mapped[str] = mapped_column(String, ForeignKey("product.product_id"), primary_key=True)
    saved_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    user: Mapped["User"] = relationship(back_populates="saved_results")
    product: Mapped["Product"] = relationship(back_populates="saved_by")
