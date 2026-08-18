from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ProductIngredient(Base):
    __tablename__ = "product_ingredient"

    product_id: Mapped[str] = mapped_column(
        String, ForeignKey("product.product_id"), primary_key=True
    )
    ingredient_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ingredient.ingredient_id"), primary_key=True
    )
    label_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    matched_text: Mapped[str | None] = mapped_column(String, nullable=True)

    product: Mapped["Product"] = relationship(back_populates="product_ingredients")
    ingredient: Mapped["Ingredient"] = relationship(back_populates="product_ingredients")
