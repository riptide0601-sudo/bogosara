from pydantic import BaseModel


class PurposeCount(BaseModel):
    label: str
    count: int
    total: int
