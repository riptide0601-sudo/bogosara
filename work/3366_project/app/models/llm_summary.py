from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class LLMSummary(Base):
    __tablename__ = "llm_summary"

    ingredient_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ingredient.ingredient_id"), primary_key=True
    )
    summary_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    benefit_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    caution_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    usage_reason_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    caution_group_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    combo_recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary_generated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    ingredient: Mapped["Ingredient"] = relationship(back_populates="llm_summary")
