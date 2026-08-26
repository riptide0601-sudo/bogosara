from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class IngredientFamilyMember(Base):
    __tablename__ = "ingredient_family_member"

    family_id: Mapped[int] = mapped_column(
        ForeignKey("ingredient_family.family_id"), primary_key=True
    )
    ingredient_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ingredient.ingredient_id"), primary_key=True
    )

    family: Mapped["IngredientFamily"] = relationship(back_populates="members")
    ingredient: Mapped["Ingredient"] = relationship()
