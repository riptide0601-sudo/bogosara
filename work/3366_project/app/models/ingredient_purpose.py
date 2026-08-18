from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class IngredientPurpose(Base):
    __tablename__ = "ingredient_purpose"

    ingredient_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ingredient.ingredient_id"), primary_key=True
    )
    purpose_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("purpose.purpose_id"), primary_key=True
    )

    ingredient: Mapped["Ingredient"] = relationship(back_populates="ingredient_purposes")
    purpose: Mapped["Purpose"] = relationship(back_populates="ingredient_purposes")
