import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserMeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    name: str
    picture_url: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    is_admin: bool


class AdminUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    name: str
    picture_url: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class AdminUserListResponse(BaseModel):
    items: list[AdminUserResponse]
    total: int
    page: int
    size: int
    pages: int
