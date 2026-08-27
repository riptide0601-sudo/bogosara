from sqlalchemy import JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class IngredientFamily(Base):
    """"히알루론산", "PDRN" 같은 마케팅 용어 하나가 가리키는 성분 계열.

    두 기능이 이 테이블을 같이 쓴다:
    - "비슷한 제품과 비교하면"(scripts/backfill_ingredient_families.py, app/routers/products.py
      get_product_family_rank) — DB 전체 성분 대상 키워드 매칭, product_family_member로
      비교 대상 제품을 사람이 큐레이션.
    - "상품명 성분, 진짜 들어있나요?"(app/marketing_families.py) — 지정 상품 기준,
      marketing_terms(상품명 매칭용 표기 후보)와 basis_note를 추가로 쓴다.

    `marketing_terms`/`basis_note`는 후자 전용이라 전자가 만든 계열(예: "판토텐산(B5) 계열")은
    비어 있을 수 있다 — nullable이라 문제 없다.
    """

    __tablename__ = "ingredient_family"

    family_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    family_name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    marketing_terms: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    basis_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    members: Mapped[list["IngredientFamilyMember"]] = relationship(
        back_populates="family", cascade="all, delete-orphan"
    )
