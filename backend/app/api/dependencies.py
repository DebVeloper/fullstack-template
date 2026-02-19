from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.exceptions import ForbiddenException, UnauthorizedException
from app.core.security import verify_access_token
from app.models.user import User
from app.repositories.user_repository import user_repository

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def normalize_email(email: str) -> str:
    return email.strip().casefold()


def is_admin_email(*, user_email: str, admin_email: str) -> bool:
    return normalize_email(user_email) == normalize_email(admin_email)


@dataclass(slots=True)
class AdminPrincipal:
    user: User
    admin_email: str


async def get_current_user(
    db: Annotated[AsyncSession, Depends(get_db)],
    token: Annotated[str, Depends(oauth2_scheme)],
) -> User:
    token_payload = verify_access_token(token)

    try:
        user_id = UUID(token_payload.sub)
    except ValueError as exc:
        raise UnauthorizedException(message="Invalid token payload") from exc

    user = await user_repository.get_by_id(db, user_id=user_id)
    if user is None or not user.is_active or user.deleted_at is not None:
        raise UnauthorizedException(message="User not found or inactive")

    return user


async def require_admin(
    current_user: Annotated[User, Depends(get_current_user)],
) -> AdminPrincipal:
    admin_email = get_settings().ADMIN_EMAIL
    if not is_admin_email(user_email=current_user.email, admin_email=admin_email):
        raise ForbiddenException(message="Admin access required")

    return AdminPrincipal(user=current_user, admin_email=admin_email)
