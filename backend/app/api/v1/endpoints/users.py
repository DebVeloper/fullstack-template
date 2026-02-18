from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_user
from app.core.config import get_settings
from app.models.user import User
from app.schemas.user import UserMeResponse

router = APIRouter(tags=["users"])


def normalize_email(email: str) -> str:
    return email.strip().casefold()


def is_admin_email(*, user_email: str, admin_email: str) -> bool:
    return normalize_email(user_email) == normalize_email(admin_email)


@router.get("/me", response_model=UserMeResponse)
async def get_me(
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserMeResponse:
    is_admin = is_admin_email(
        user_email=current_user.email,
        admin_email=get_settings().ADMIN_EMAIL,
    )
    return UserMeResponse(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        picture_url=current_user.picture_url,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at,
        is_admin=is_admin,
    )
