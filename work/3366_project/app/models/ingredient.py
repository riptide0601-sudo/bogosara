from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Ingredient(Base):
    __tablename__ = "ingredient"

    ingredient_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name_kr: Mapped[str | None] = mapped_column(String, index=True, nullable=True)
    name_en: Mapped[str | None] = mapped_column(String, index=True, nullable=True)
    synonyms: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    safety_level: Mapped[str | None] = mapped_column(String, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary_generated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    product_ingredients: Mapped[list["ProductIngredient"]] = relationship(
        back_populates="ingredient", cascade="all, delete-orphan"
    )
    ingredient_purposes: Mapped[list["IngredientPurpose"]] = relationship(
        back_populates="ingredient", cascade="all, delete-orphan"
    )
    llm_summary: Mapped["LLMSummary | None"] = relationship(
        back_populates="ingredient", cascade="all, delete-orphan", uselist=False
    )
