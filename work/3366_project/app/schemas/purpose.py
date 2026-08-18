from pydantic import BaseModel, ConfigDict


class PurposeBase(BaseModel):
    purpose_name: str
    description: str | None = None


class PurposeCreate(PurposeBase):
    pass


class PurposeRead(PurposeBase):
    model_config = ConfigDict(from_attributes=True)

    purpose_id: int
