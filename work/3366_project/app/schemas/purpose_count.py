from pydantic import BaseModel


class PurposeCount(BaseModel):
    label: str
    count: int
    total: int
    # purpose.description — 라벨과 정확히 이름이 같은 배합목적(또는 그중 설명이 있는 것) 기준.
    # 둘 다 없으면 None(프론트는 이때 느낌표 아이콘 자체를 숨긴다 — 없는 설명을 지어내지 않음).
    description: str | None = None
