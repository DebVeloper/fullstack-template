from uuid import UUID

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException, NotFoundException
from app.models.user import User
from app.repositories.user_repository import user_repository
from app.schemas.user import AdminUserListResponse
from app.services import auth_service

SUPERADMIN_PROTECTED_CODE = "SUPERADMIN_PROTECTED"
SUPERADMIN_PROTECTED_MESSAGE = "Superadmin account cannot be modified"


def normalize_email(email: str) -> str:
    return email.strip().casefold()


def is_superadmin_email(*, user_email: str, admin_email: str) -> bool:
    return normalize_email(user_email) == normalize_email(admin_email)


def _ensure_not_superadmin(*, target_user: User, admin_email: str) -> None:
    if is_superadmin_email(user_email=target_user.email, admin_email=admin_email):
        raise AppException(
            status_code=403,
            code=SUPERADMIN_PROTECTED_CODE,
            message=SUPERADMIN_PROTECTED_MESSAGE,
        )


async def list_users(
    db: AsyncSession,
    *,
    page: int,
    size: int,
    include_deleted: bool,
) -> AdminUserListResponse:
    users = await user_repository.list_users(
        db,
        page=page,
        size=size,
        include_deleted=include_deleted,
    )
    total = await user_repository.count_users(db, include_deleted=include_deleted)
    pages = (total + size - 1) // size if total > 0 else 0
    return AdminUserListResponse(
        items=list(users),
        total=total,
        page=page,
        size=size,
        pages=pages,
    )


async def lock_user(
    db: AsyncSession,
    redis: Redis,
    *,
    user_id: UUID,
    admin_email: str,
) -> User:
    user = await user_repository.get_by_id(db, user_id=user_id)
    if user is None:
        raise NotFoundException(message="User not found")

    _ensure_not_superadmin(target_user=user, admin_email=admin_email)

    updated_user = await user_repository.set_active_status(
        db, user=user, is_active=False
    )
    await auth_service.revoke_all_sessions(redis, user_id=str(updated_user.id))
    return updated_user


async def unlock_user(
    db: AsyncSession,
    *,
    user_id: UUID,
) -> User:
    user = await user_repository.get_by_id(db, user_id=user_id)
    if user is None:
        raise NotFoundException(message="User not found")

    return await user_repository.set_active_status(db, user=user, is_active=True)


async def delete_user(
    db: AsyncSession,
    redis: Redis,
    *,
    user_id: UUID,
    admin_email: str,
) -> User:
    user = await user_repository.get_by_id(db, user_id=user_id)
    if user is None:
        raise NotFoundException(message="User not found")

    _ensure_not_superadmin(target_user=user, admin_email=admin_email)

    deleted_user = await user_repository.delete(db, user=user)
    await auth_service.revoke_all_sessions(redis, user_id=str(deleted_user.id))
    return deleted_user
