from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

# 피부 타입 → 피부 고민 → 필요한 성분 기능 → 실제 제품 성분 → 적합도 점수 → 추천
# 4가지 피부 타입 고정 (AAD 분류 기준: 지성/복합성/건성/민감성).
SKIN_TYPES = ["지성", "복합성", "건성", "민감성"]

# 근거 수준 — 브랜드 마케팅 주장과 실제 문헌 근거를 구분하기 위한 척도.
EVIDENCE_LEVELS = {
    "A": "Systematic Review / Meta-analysis",
    "B": "Randomized Controlled Trial",
    "C": "임상시험/관찰연구",
    "D": "피부과 전문기관 가이드",
    "E": "전문가 의견/브랜드 자료",
}


class IngredientSkinScore(Base):
    """성분 하나가 특정 피부 타입에 얼마나 적합한지를 나타내는 점수.

    ingredient_purpose(배합목적)와는 별개 축이다 — 배합목적은 "이 성분이 뭘 하는가"이고
    이 테이블은 "그래서 이 피부 타입에는 얼마나 맞는가"를 담는다. 점수는 -3(피하는 게
    좋음) ~ +3(적극 권장) 범위이며, 제품 전체 적합도는 이 점수들을 합산해 계산한다
    (app/skin_fit.py 참고).
    """

    __tablename__ = "ingredient_skin_score"

    ingredient_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ingredient.ingredient_id"), primary_key=True
    )
    skin_type: Mapped[str] = mapped_column(String, primary_key=True)  # SKIN_TYPES 중 하나

    score: Mapped[int] = mapped_column(Integer, nullable=False)  # -3 ~ +3
    function: Mapped[str | None] = mapped_column(String, nullable=True)  # Humectant/Occlusive/Emollient 등
    evidence_level: Mapped[str | None] = mapped_column(String, nullable=True)  # EVIDENCE_LEVELS 키
    source: Mapped[str | None] = mapped_column(String, nullable=True)  # "AAD", "PubMed", "대한화장품협회" 등
    caution: Mapped[str | None] = mapped_column(Text, nullable=True)

    ingredient: Mapped["Ingredient"] = relationship()
