from secrets import compare_digest
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Response, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.exceptions import NotFoundException, UnauthorizedException
from app.core.redis import get_redis
from app.schemas.auth import (
    GoogleExchangeRequest,
    RefreshRequest,
    TestLoginRequest,
    TokenResponse,
)
from app.services import auth_service

router = APIRouter(tags=["auth"])


@router.post("/refresh", response_model=TokenResponse)
async def refresh_tokens(
    body: RefreshRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> TokenResponse:
    return await auth_service.refresh(db, redis, refresh_token=body.refresh_token)


@router.post("/google/exchange", response_model=TokenResponse)
async def exchange_google_code(
    body: GoogleExchangeRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> TokenResponse:
    return await auth_service.exchange_google_code_for_tokens(
        db,
        redis,
        code=body.code,
        code_verifier=body.code_verifier,
    )


@router.post("/test-login", response_model=TokenResponse, include_in_schema=False)
async def test_login(
    body: TestLoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
    x_test_auth_secret: Annotated[str | None, Header()] = None,
) -> TokenResponse:
    settings = get_settings()

    if not settings.AUTH_TEST_MODE:
        raise NotFoundException()

    configured_secret = settings.AUTH_TEST_SECRET
    if (
        configured_secret is None
        or x_test_auth_secret is None
        or not compare_digest(x_test_auth_secret, configured_secret)
    ):
        raise UnauthorizedException(message="Invalid test auth secret")

    return await auth_service.test_login(
        db,
        redis,
        email=str(body.email),
        name=body.name,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    body: RefreshRequest,
    redis: Annotated[Redis, Depends(get_redis)],
) -> Response:
    await auth_service.logout(redis, refresh_token=body.refresh_token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
