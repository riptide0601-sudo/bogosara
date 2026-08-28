import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _new_history_id() -> str:
    return f"rh-{uuid.uuid4().hex[:12]}"


class RoutineHistory(Base):
    """마이페이지/내 화장품 조합 화면의 "이 조합 저장하기" — 그 시점의 조합(product_ids)을
    스냅샷으로 남긴다. RoutineItem(지금 등록된 조합, 언제든 추가/삭제 가능)과 달리 이건
    한 번 저장하면 안 바뀌는 기록이라 별도 테이블로 둔다. headline은 저장 시점의
    app/routine_analysis.py 분석 문장을 그대로 박아둬서, 나중에 제품이 삭제/변경돼도
    "그때 이런 조합이었다"는 문구가 유지된다."""

    __tablename__ = "routine_history"

    history_id: Mapped[str] = mapped_column(String, primary_key=True, default=_new_history_id)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("app_user.user_id"), index=True)
    product_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    headline: Mapped[str] = mapped_column(String, nullable=False)
    saved_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    user: Mapped["User"] = relationship(back_populates="routine_history_entries")
