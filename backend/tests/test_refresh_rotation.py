import os
from collections.abc import AsyncGenerator
from inspect import isawaitable
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.redis import get_redis
from app.core.security import verify_access_token
from app.main import app
from app.models.user import User

TEST_SECRET = "jwt-test-secret-key-with-at-least-32-bytes"
REFRESH_TOKEN_TTL_SECONDS = 7 * 24 * 60 * 60
REFRESH_KEY_PREFIX = "refresh_token:"
FAMILY_KEY_PREFIX = "token_family:"
USER_FAMILIES_PREFIX = "user_families:"


@pytest.fixture(autouse=True)
def set_secret_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SECRET_KEY", TEST_SECRET)


@pytest.fixture
async def redis_session() -> AsyncGenerator[Redis, None]:
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    redis = Redis.from_url(redis_url, decode_responses=True)
    await redis.flushdb()
    yield redis
    await redis.flushdb()
    await redis.aclose()


@pytest.fixture
async def auth_client(
    db_session: AsyncSession,
    redis_session: Redis,
) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    async def override_get_redis() -> AsyncGenerator[Redis, None]:
        yield redis_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        yield client

    app.dependency_overrides.clear()


async def seed_refresh_family(
    redis: Redis,
    *,
    user_id: str,
    family_id: str,
    refresh_token: str,
) -> None:
    await redis.set(
        f"{REFRESH_KEY_PREFIX}{refresh_token}",
        f"{user_id}:{family_id}",
        ex=REFRESH_TOKEN_TTL_SECONDS,
    )
    await redis.set(
        f"{FAMILY_KEY_PREFIX}{family_id}",
        refresh_token,
        ex=REFRESH_TOKEN_TTL_SECONDS,
    )
    await resolve_redis_result(
        redis.sadd(f"{USER_FAMILIES_PREFIX}{user_id}", family_id)
    )


async def resolve_redis_result(value: object) -> object:
    if isawaitable(value):
        return await value
    return value


async def test_refresh_rotates_token_and_sets_old_token_grace_ttl(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    redis_session: Redis,
) -> None:
    user = User(
        google_sub="refresh-rotation-user-sub",
        email="rotation-user@example.com",
        name="Rotation User",
        picture_url="https://example.com/rotation-user.png",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    old_refresh_token = str(uuid4())
    family_id = str(uuid4())
    await seed_refresh_family(
        redis_session,
        user_id=str(user.id),
        family_id=family_id,
        refresh_token=old_refresh_token,
    )

    response = await auth_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": old_refresh_token},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["refresh_token"] != old_refresh_token

    token_payload = verify_access_token(body["access_token"])
    assert token_payload.sub == str(user.id)

    old_mapping = await redis_session.get(f"{REFRESH_KEY_PREFIX}{old_refresh_token}")
    assert old_mapping == f"{user.id}:{family_id}"

    old_ttl = await redis_session.ttl(f"{REFRESH_KEY_PREFIX}{old_refresh_token}")
    assert 0 < old_ttl <= 10

    new_refresh_token = body["refresh_token"]
    family_token = await redis_session.get(f"{FAMILY_KEY_PREFIX}{family_id}")
    assert family_token == new_refresh_token

    new_mapping = await redis_session.get(f"{REFRESH_KEY_PREFIX}{new_refresh_token}")
    assert new_mapping == f"{user.id}:{family_id}"


async def test_refresh_allows_old_token_reuse_within_grace_period(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    redis_session: Redis,
) -> None:
    user = User(
        google_sub="refresh-grace-user-sub",
        email="grace-user@example.com",
        name="Grace User",
        picture_url="https://example.com/grace-user.png",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    old_refresh_token = str(uuid4())
    family_id = str(uuid4())
    await seed_refresh_family(
        redis_session,
        user_id=str(user.id),
        family_id=family_id,
        refresh_token=old_refresh_token,
    )

    first_response = await auth_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": old_refresh_token},
    )
    assert first_response.status_code == 200
    first_body = first_response.json()

    second_response = await auth_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": old_refresh_token},
    )

    assert second_response.status_code == 200
    second_body = second_response.json()

    assert second_body["token_type"] == "bearer"
    assert second_body["refresh_token"] == first_body["refresh_token"]
    verify_access_token(second_body["access_token"])


async def test_logout_revokes_token_family_and_returns_204(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    redis_session: Redis,
) -> None:
    user = User(
        google_sub="refresh-logout-user-sub",
        email="logout-user@example.com",
        name="Logout User",
        picture_url="https://example.com/logout-user.png",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    refresh_token = str(uuid4())
    family_id = str(uuid4())
    await seed_refresh_family(
        redis_session,
        user_id=str(user.id),
        family_id=family_id,
        refresh_token=refresh_token,
    )

    response = await auth_client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": refresh_token},
    )

    assert response.status_code == 204

    assert await redis_session.get(f"{REFRESH_KEY_PREFIX}{refresh_token}") is None
    assert await redis_session.get(f"{FAMILY_KEY_PREFIX}{family_id}") is None
    sessions = await resolve_redis_result(
        redis_session.smembers(f"{USER_FAMILIES_PREFIX}{user.id}")
    )
    assert sessions == set()
