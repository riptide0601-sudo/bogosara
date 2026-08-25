import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _new_product_id() -> str:
    return f"p-{uuid.uuid4().hex[:12]}"


class Product(Base):
    __tablename__ = "product"

    product_id: Mapped[str] = mapped_column(
        String, primary_key=True, default=_new_product_id
    )
    product_name: Mapped[str] = mapped_column(String, nullable=False)
    brand: Mapped[str | None] = mapped_column(String, nullable=True)
    category: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 카드 앞면 "성분 구성을 살펴보면" 본문 — summary(한 줄 요약)와는 별개 필드. LLM 붙이기 전엔 항상 비어있다.
    composition_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary_generated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # app/core_ingredient_selector.py의 analyze_product_from_orm() 결과를 JSON 배열
    # 문자열로 저장한다 (성분/효능 각각 최대 5개). scripts/backfill_key_ingredients.py로 채운다.
    key_ingredients: Mapped[str | None] = mapped_column(Text, nullable=True)
    key_purposes: Mapped[str | None] = mapped_column(Text, nullable=True)

    product_ingredients: Mapped[list["ProductIngredient"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )
    product_concerns: Mapped[list["ProductConcern"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )
    saved_by: Mapped[list["SavedResult"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )
    in_routines: Mapped[list["RoutineItem"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )
