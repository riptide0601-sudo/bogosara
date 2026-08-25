import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _new_user_id() -> str:
    return f"u-{uuid.uuid4().hex[:12]}"


class User(Base):
    """마이페이지 계정. 비밀번호는 bcrypt 해시로만 저장하고 평문은 절대 갖고 있지 않는다
    (해싱/검증은 app/auth.py의 hash_password/verify_password 참고). skin_types/
    watched_ingredients는 마이페이지 "나의 피부 프로필" 섹션 그대로 — 검색·스캔 결과에서
    해당 성분이 나올 때 미리 표시해주는 기능의 저장소다."""

    __tablename__ = "app_user"

    user_id: Mapped[str] = mapped_column(String, primary_key=True, default=_new_user_id)
    nickname: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    joined_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    notify_alerts: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    skin_types: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    watched_ingredients: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)

    saved_results: Mapped[list["SavedResult"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
