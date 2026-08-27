from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class IngredientFamilyMember(Base):
    """`IngredientFamily` 계열 하나에 실제로 속하는 성분 하나.

    `match_type`/`basis_detail`은 "상품명 성분, 진짜 들어있나요?" 기능 전용(정확(어근일치)/
    정확(DB 정의문 근거)/유연물질(관련이지만 다른 물질) — docs/marketing_terms/alias_table.csv
    참고). "비슷한 제품과 비교하면" 기능(scripts/backfill_ingredient_families.py)이 만든
    행은 이 두 컬럼이 비어 있다 — nullable이라 문제 없고, 그 기능은 애초에 이 두 컬럼을 안 쓴다.
    """

    __tablename__ = "ingredient_family_member"

    family_id: Mapped[int] = mapped_column(
        ForeignKey("ingredient_family.family_id"), primary_key=True
    )
    ingredient_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ingredient.ingredient_id"), primary_key=True
    )
    match_type: Mapped[str | None] = mapped_column(String, nullable=True)
    basis_detail: Mapped[str | None] = mapped_column(Text, nullable=True)

    family: Mapped["IngredientFamily"] = relationship(back_populates="members")
    ingredient: Mapped["Ingredient"] = relationship()
