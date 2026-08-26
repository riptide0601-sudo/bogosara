from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class IngredientFamily(Base):
    __tablename__ = "ingredient_family"

    family_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    family_name: Mapped[str] = mapped_column(String, unique=True, nullable=False)

    members: Mapped[list["IngredientFamilyMember"]] = relationship(
        back_populates="family", cascade="all, delete-orphan"
    )
