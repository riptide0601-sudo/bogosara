from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Purpose(Base):
    __tablename__ = "purpose"

    purpose_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    purpose_name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    ingredient_purposes: Mapped[list["IngredientPurpose"]] = relationship(
        back_populates="purpose", cascade="all, delete-orphan"
    )
