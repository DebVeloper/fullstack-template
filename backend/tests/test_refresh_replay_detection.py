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


async def test_refresh_detects_replay_and_revokes_all_user_sessions(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    redis_session: Redis,
) -> None:
    user = User(
        google_sub="refresh-replay-user-sub",
        email="replay-user@example.com",
        name="Replay User",
        picture_url="https://example.com/replay-user.png",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    replay_family_id = str(uuid4())
    replayed_old_token = str(uuid4())
    current_replay_family_token = str(uuid4())

    await seed_refresh_family(
        redis_session,
        user_id=str(user.id),
        family_id=replay_family_id,
        refresh_token=replayed_old_token,
    )
    await redis_session.set(
        f"{FAMILY_KEY_PREFIX}{replay_family_id}",
        current_replay_family_token,
        ex=REFRESH_TOKEN_TTL_SECONDS,
    )
    await redis_session.set(
        f"{REFRESH_KEY_PREFIX}{current_replay_family_token}",
        f"{user.id}:{replay_family_id}",
        ex=REFRESH_TOKEN_TTL_SECONDS,
    )

    second_family_id = str(uuid4())
    second_family_token = str(uuid4())
    await seed_refresh_family(
        redis_session,
        user_id=str(user.id),
        family_id=second_family_id,
        refresh_token=second_family_token,
    )

    response = await auth_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": replayed_old_token},
    )

    assert response.status_code == 401
    assert response.json() == {
        "error": {
            "code": "UNAUTHORIZED",
            "message": "Token reuse detected. All sessions revoked.",
            "details": None,
        }
    }

    sessions = await resolve_redis_result(
        redis_session.smembers(f"{USER_FAMILIES_PREFIX}{user.id}")
    )
    assert sessions == set()
    assert await redis_session.get(f"{FAMILY_KEY_PREFIX}{replay_family_id}") is None
    assert await redis_session.get(f"{FAMILY_KEY_PREFIX}{second_family_id}") is None
    assert (
        await redis_session.get(f"{REFRESH_KEY_PREFIX}{current_replay_family_token}")
        is None
    )
    assert await redis_session.get(f"{REFRESH_KEY_PREFIX}{second_family_token}") is None
