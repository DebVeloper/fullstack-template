from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import AdminPrincipal, require_admin
from app.core.database import get_db
from app.core.redis import get_redis
from app.schemas.user import AdminUserListResponse, AdminUserResponse
from app.services import admin_user_service

router = APIRouter(tags=["admin-users"])


@router.get("", response_model=AdminUserListResponse)
async def list_admin_users(
    _admin: Annotated[AdminPrincipal, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
    include_deleted: Annotated[
        bool,
        Query(
            description="Deprecated: retained for compatibility only",
            deprecated=True,
        ),
    ] = False,
) -> AdminUserListResponse:
    return await admin_user_service.list_users(
        db,
        page=page,
        size=size,
        include_deleted=include_deleted,
    )


@router.patch("/{user_id}/lock", response_model=AdminUserResponse)
async def lock_user(
    user_id: UUID,
    admin: Annotated[AdminPrincipal, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> AdminUserResponse:
    user = await admin_user_service.lock_user(
        db,
        redis,
        user_id=user_id,
        admin_email=admin.admin_email,
    )
    return AdminUserResponse.model_validate(user)


@router.patch("/{user_id}/unlock", response_model=AdminUserResponse)
async def unlock_user(
    user_id: UUID,
    _admin: Annotated[AdminPrincipal, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AdminUserResponse:
    user = await admin_user_service.unlock_user(db, user_id=user_id)
    return AdminUserResponse.model_validate(user)


@router.delete(
    "/{user_id}",
    response_model=AdminUserResponse,
    operation_id="soft_delete_user",
)
async def delete_user(
    user_id: UUID,
    admin: Annotated[AdminPrincipal, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> AdminUserResponse:
    user = await admin_user_service.delete_user(
        db,
        redis,
        user_id=user_id,
        admin_email=admin.admin_email,
    )
    return AdminUserResponse.model_validate(user)
