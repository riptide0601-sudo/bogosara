from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class RoutineItem(Base):
    """마이페이지 "내 화장품 조합" — 유저가 실제로 쓰는 제품으로 등록한 기록.
    (user_id, product_id) 복합키라 같은 제품을 다시 등록해도 새 행이 생기지 않는다.
    app/routine_analysis.py가 이 목록 전체의 전성분을 모아 조합 분석에 쓴다."""

    __tablename__ = "routine_item"

    user_id: Mapped[str] = mapped_column(String, ForeignKey("app_user.user_id"), primary_key=True)
    product_id: Mapped[str] = mapped_column(String, ForeignKey("product.product_id"), primary_key=True)
    added_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    user: Mapped["User"] = relationship(back_populates="routine_items")
    product: Mapped["Product"] = relationship(back_populates="in_routines")
