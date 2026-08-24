from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

# 피부 타입 → 피부 고민 → 필요한 성분 기능 → 실제 제품 성분 → 적합도 점수 → 추천
# 4가지 피부 타입 고정 (AAD 분류 기준: 지성/복합성/건성/민감성).
SKIN_TYPES = ["지성", "복합성", "건성", "민감성"]


class IngredientSkinScore(Base):
    """성분 하나가 특정 피부 타입에 위험하거나(is_risk=True) 잘 맞는다고(is_risk=False)
    확인된 경우를 기록한다.

    [2026-08-21 개편] 원래는 -3(피하는 게 좋음)~+3(적극 권장) 점수를 매겨 제품 전체
    적합도를 합산하는 방식이었으나, 점수 자체가 근거 없는 가짜 정밀도라 폐기했다
    (app/skin_fit.py 참고). `score`/`evidence_level` 컬럼도 같은 이유로 제거했다 —
    "몇 점인지"가 아니라 "위험한지/잘 맞는지"만 본다.
    [2026-08-24 확장] 처음엔 위험 성분만 기록했지만(is_risk 컬럼 없이 전부 위험이었음),
    궁합성분(추천 성분) 데이터를 같은 테이블에 넣기 위해 is_risk로 위험/궁합을 구분한다.
    app/skin_fit.py의 compute_skin_risk()는 is_risk=True인 행만 읽으므로 기존 위험
    경고 동작은 그대로 유지된다. skin_type에는 SKIN_TYPES 4종 외에 "전체"도 들어올 수
    있다 — 향료 알레르겐처럼 피부타입과 무관하게 개인 감작 여부로 생기는 위험을 표현할
    때 쓴다.
    """

    __tablename__ = "ingredient_skin_score"

    ingredient_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ingredient.ingredient_id"), primary_key=True
    )
    skin_type: Mapped[str] = mapped_column(String, primary_key=True)  # SKIN_TYPES 4종 또는 "전체"

    is_risk: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    function: Mapped[str | None] = mapped_column(String, nullable=True)  # 위험 유형/효능 유형
    source: Mapped[str | None] = mapped_column(String, nullable=True)  # 근거 논문/기관 자료 (제목 + URL)
    caution: Mapped[str | None] = mapped_column(Text, nullable=True)  # 위험 사유 또는 궁합 근거 설명

    ingredient: Mapped["Ingredient"] = relationship()
