from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class IngredientRelation(Base):
    __tablename__ = "ingredient_relation"

    relation_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ingredient_a_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ingredient.ingredient_id"), nullable=False
    )
    ingredient_b_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ingredient.ingredient_id"), nullable=False
    )
    relation_type: Mapped[str] = mapped_column(String, nullable=False)  # "시너지" | "악화"
    user_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str | None] = mapped_column(Text, nullable=True)

    ingredient_a: Mapped["Ingredient"] = relationship(foreign_keys=[ingredient_a_id])
    ingredient_b: Mapped["Ingredient"] = relationship(foreign_keys=[ingredient_b_id])
