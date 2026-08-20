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
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary_generated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    key_ingredients: Mapped[str | None] = mapped_column(Text, nullable=True)
    key_purposes: Mapped[str | None] = mapped_column(Text, nullable=True)

    product_ingredients: Mapped[list["ProductIngredient"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )
