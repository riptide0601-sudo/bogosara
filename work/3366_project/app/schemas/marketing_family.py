from pydantic import BaseModel


class MatchedFamilyIngredient(BaseModel):
    ingredient_id: int
    name_kr: str | None
    label_rank: int | None
    # matched_text에서 뽑은 용량 표기(예: "29,049ppm"). 원문에 없으면 None — 지어내지 않는다.
    dosage: str | None
    match_type: str
    is_key_ingredient: bool


class MatchedFamily(BaseModel):
    family_id: int
    name: str
    # 상품명에 이 계열의 마케팅 용어가 실제로 등장했는지 — true면 1순위(상품명 용어),
    # false면 2순위(일반 매칭 계열). 화면에서 배지/설명 문구를 다르게 보여줄 때 쓴다.
    from_product_name: bool
    ingredients: list[MatchedFamilyIngredient]
