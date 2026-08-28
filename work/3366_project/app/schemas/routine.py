from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RoutineItemCreate(BaseModel):
    product_id: str


class RoutineItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    product_id: str
    product_name: str
    brand: str | None = None
    category: str | None = None
    added_at: datetime
    # 제품 하나에 대한 간단 설명 — product.summary(LLM 요약)가 있으면 그대로, 없으면 빈 문자열
    # (app/routine_analysis.py의 build_item_description 참고). 핵심 성분은 별도로
    # key_ingredients에 리스트 그대로 내려주므로 여기서 문장으로 대신 만들지 않는다.
    description: str = ""
    key_ingredients: list[str] = []
    key_purposes: list[str] = []


class RoutineIngredientNoteRead(BaseModel):
    ingredient_id: int
    name_kr: str | None = None
    # ingredient.summary — 성분 자체에 대한 일반 설명(항상 보임). reason은 이 피부타입에
    # 왜 위험/궁합인지에 대한 설명(호버 툴팁으로만 보임) — app/routine_analysis.py 참고.
    description: str | None = None
    risk_type: str | None = None
    reason: str | None = None


class RoutineSkinTypeNoteRead(BaseModel):
    skin_type: str
    risk_ingredients: list[RoutineIngredientNoteRead] = []
    good_ingredients: list[RoutineIngredientNoteRead] = []


class RoutineHistoryProductRead(BaseModel):
    product_id: str
    product_name: str
    brand: str | None = None


class RoutineRelationNoteRead(BaseModel):
    relation_type: str  # "시너지" | "악화"
    ingredient_a: str
    ingredient_b: str
    message: str | None = None
    # 루틴에서 실제로 ingredient_a/b를 담고 있는 제품(대표 1개씩). "악화"일 때만
    # alternatives_a/b(대체 후보)도 같이 온다 — "시너지"는 대체가 필요 없어 비어 있다.
    product_a: RoutineHistoryProductRead | None = None
    product_b: RoutineHistoryProductRead | None = None
    alternatives_a: list[RoutineHistoryProductRead] = []
    alternatives_b: list[RoutineHistoryProductRead] = []


class RoutineHistoryRead(BaseModel):
    history_id: str
    headline: str
    # 저장 당시 담겨 있던 제품 개수 — 이후 제품이 DB에서 지워져도 이 값은 안 바뀐다
    # (products 리스트는 지워진 제품만큼 줄어들 수 있음).
    product_count: int
    products: list[RoutineHistoryProductRead] = []
    saved_at: datetime


class RoutineAnalysisRead(BaseModel):
    product_count: int
    ingredient_count: int
    headline: str
    # 루틴 전체 제품들의 key_purposes를 모아 만든, 조합 전체에 대한 한 단락 설명.
    overall_description: str
    hydration_note: str
    hydration_count: int = 0
    occlusion_count: int = 0
    hydration_ingredients: list[str] = []
    occlusion_ingredients: list[str] = []
    skin_type_notes: list[RoutineSkinTypeNoteRead] = []
    # 서로 다른 제품에 걸쳐 있는 성분 조합 중 ingredient_relation에 등록된 시너지/악화 쌍.
    relations: list[RoutineRelationNoteRead] = []
