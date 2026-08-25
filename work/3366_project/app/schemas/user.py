from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserSignup(BaseModel):
    email: str
    nickname: str
    password: str = Field(min_length=8)


class UserLogin(BaseModel):
    email: str
    password: str


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: str
    nickname: str
    email: str
    joined_at: datetime
    notify_alerts: bool


class UserUpdate(BaseModel):
    nickname: str | None = None
    notify_alerts: bool | None = None


class TokenRead(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead


class SkinProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    skin_types: list[str]
    watched_ingredients: list[str]


class SkinProfileUpdate(BaseModel):
    skin_types: list[str] | None = None
    watched_ingredients: list[str] | None = None


class SavedResultCreate(BaseModel):
    product_id: str


class SavedResultRead(BaseModel):
    product_id: str
    product_name: str
    brand: str | None = None
    category: str | None = None
    saved_at: datetime
