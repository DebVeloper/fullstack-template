import os
from collections.abc import AsyncGenerator, Generator
from datetime import datetime
from inspect import isawaitable
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.redis import get_redis
from app.core.security import create_access_token
from app.main import app
from app.models.user import User

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/app",
)
os.environ.setdefault(
    "DATABASE_URL_TEST",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/app",
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("ADMIN_EMAIL", "admin@example.com")
os.environ.setdefault("GOOGLE_OAUTH_CLIENT_ID", "test-client-id")
os.environ.setdefault("GOOGLE_OAUTH_CLIENT_SECRET", "test-client-secret")
os.environ.setdefault(
    "GOOGLE_OAUTH_REDIRECT_URI",
    "http://localhost:3000/api/auth/google/callback",
)
os.environ.setdefault("ALLOWED_ORIGINS", "http://localhost:3000")

REFRESH_TOKEN_TTL_SECONDS = 7 * 24 * 60 * 60
REFRESH_KEY_PREFIX = "refresh_token:"
FAMILY_KEY_PREFIX = "token_family:"
USER_FAMILIES_PREFIX = "user_families:"
TEST_SECRET = "jwt-test-secret-key-with-at-least-32-bytes"


@pytest.fixture(autouse=True)
def set_secret_key(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    monkeypatch.setenv("SECRET_KEY", TEST_SECRET)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
async def redis_session() -> AsyncGenerator[Redis, None]:
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    redis = Redis.from_url(redis_url, decode_responses=True)
    await redis.flushdb()
    yield redis
    await redis.flushdb()
    await redis.aclose()


@pytest.fixture
async def admin_client(
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


async def create_user(
    db_session: AsyncSession,
    *,
    email: str,
    name: str,
    is_active: bool = True,
    deleted_at: datetime | None = None,
) -> User:
    user = User(
        google_sub=str(uuid4()),
        email=email,
        name=name,
        picture_url=f"https://example.com/{uuid4()}.png",
        is_active=is_active,
        deleted_at=deleted_at,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


def auth_headers(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


async def resolve_redis_result(value: object) -> object:
    if isawaitable(value):
        return await value
    return value


async def seed_refresh_family(
    redis: Redis,
    *,
    user_id: str,
    family_id: str,
    refresh_token: str,
) -> None:
    await resolve_redis_result(
        redis.set(
            f"{REFRESH_KEY_PREFIX}{refresh_token}",
            f"{user_id}:{family_id}",
            ex=REFRESH_TOKEN_TTL_SECONDS,
        )
    )
    await resolve_redis_result(
        redis.set(
            f"{FAMILY_KEY_PREFIX}{family_id}",
            refresh_token,
            ex=REFRESH_TOKEN_TTL_SECONDS,
        )
    )
    await resolve_redis_result(
        redis.sadd(f"{USER_FAMILIES_PREFIX}{user_id}", family_id)
    )


async def test_admin_users_requires_admin_authorization(
    admin_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    non_admin = await create_user(
        db_session,
        email="member@example.com",
        name="Member",
    )

    response = await admin_client.get(
        "/api/v1/admin/users",
        headers=auth_headers(non_admin),
    )

    assert response.status_code == 403
    assert response.json() == {
        "error": {
            "code": "FORBIDDEN",
            "message": "Admin access required",
            "details": None,
        }
    }


async def test_admin_users_list_returns_users_by_default(
    admin_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    admin_user = await create_user(
        db_session,
        email="admin@example.com",
        name="Admin",
    )
    await create_user(
        db_session,
        email="active@example.com",
        name="Active",
    )

    response = await admin_client.get(
        "/api/v1/admin/users",
        headers=auth_headers(admin_user),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["page"] == 1
    assert body["size"] == 20
    assert body["total"] == 2
    returned_emails = {item["email"] for item in body["items"]}
    assert returned_emails == {"admin@example.com", "active@example.com"}
    assert all(item["deleted_at"] is None for item in body["items"])


async def test_admin_can_lock_and_unlock_user_and_revoke_sessions(
    admin_client: AsyncClient,
    db_session: AsyncSession,
    redis_session: Redis,
) -> None:
    admin_user = await create_user(
        db_session,
        email="admin@example.com",
        name="Admin",
    )
    target_user = await create_user(
        db_session,
        email="target@example.com",
        name="Target",
    )

    refresh_token = str(uuid4())
    family_id = str(uuid4())
    await seed_refresh_family(
        redis_session,
        user_id=str(target_user.id),
        family_id=family_id,
        refresh_token=refresh_token,
    )

    lock_response = await admin_client.patch(
        f"/api/v1/admin/users/{target_user.id}/lock",
        headers=auth_headers(admin_user),
    )

    assert lock_response.status_code == 200
    assert lock_response.json()["is_active"] is False

    await db_session.refresh(target_user)
    assert target_user.is_active is False

    lock_refresh_mapping = await resolve_redis_result(
        redis_session.get(f"{REFRESH_KEY_PREFIX}{refresh_token}")
    )
    lock_family_mapping = await resolve_redis_result(
        redis_session.get(f"{FAMILY_KEY_PREFIX}{family_id}")
    )
    assert lock_refresh_mapping is None
    assert lock_family_mapping is None
    lock_sessions = await resolve_redis_result(
        redis_session.smembers(f"{USER_FAMILIES_PREFIX}{target_user.id}")
    )
    assert lock_sessions == set()

    refresh_response = await admin_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_response.status_code == 401
    assert refresh_response.json()["error"]["code"] == "UNAUTHORIZED"

    unlock_response = await admin_client.patch(
        f"/api/v1/admin/users/{target_user.id}/unlock",
        headers=auth_headers(admin_user),
    )

    assert unlock_response.status_code == 200
    assert unlock_response.json()["is_active"] is True

    await db_session.refresh(target_user)
    assert target_user.is_active is True


async def test_admin_can_delete_user_and_revoke_sessions(
    admin_client: AsyncClient,
    db_session: AsyncSession,
    redis_session: Redis,
) -> None:
    admin_user = await create_user(
        db_session,
        email="admin@example.com",
        name="Admin",
    )
    target_user = await create_user(
        db_session,
        email="delete-target@example.com",
        name="Delete Target",
    )

    refresh_token = str(uuid4())
    family_id = str(uuid4())
    await seed_refresh_family(
        redis_session,
        user_id=str(target_user.id),
        family_id=family_id,
        refresh_token=refresh_token,
    )

    delete_response = await admin_client.delete(
        f"/api/v1/admin/users/{target_user.id}",
        headers=auth_headers(admin_user),
    )

    assert delete_response.status_code == 200
    delete_body = delete_response.json()
    assert delete_body["id"] == str(target_user.id)
    assert delete_body["email"] == "delete-target@example.com"

    user_result = await db_session.execute(
        select(User.id).where(User.id == target_user.id)
    )
    assert user_result.scalar_one_or_none() is None

    list_without_deleted_response = await admin_client.get(
        "/api/v1/admin/users",
        headers=auth_headers(admin_user),
    )
    list_without_deleted_body = list_without_deleted_response.json()
    assert list_without_deleted_response.status_code == 200
    ids_without_deleted = {
        str(item["id"]) for item in list_without_deleted_body["items"]
    }
    assert str(target_user.id) not in ids_without_deleted

    list_with_deleted_response = await admin_client.get(
        "/api/v1/admin/users",
        headers=auth_headers(admin_user),
    )
    list_with_deleted_body = list_with_deleted_response.json()
    assert list_with_deleted_response.status_code == 200
    assert list_with_deleted_body == list_without_deleted_body

    deleted_refresh_mapping = await resolve_redis_result(
        redis_session.get(f"{REFRESH_KEY_PREFIX}{refresh_token}")
    )
    deleted_family_mapping = await resolve_redis_result(
        redis_session.get(f"{FAMILY_KEY_PREFIX}{family_id}")
    )
    assert deleted_refresh_mapping is None
    assert deleted_family_mapping is None
    deleted_sessions = await resolve_redis_result(
        redis_session.smembers(f"{USER_FAMILIES_PREFIX}{target_user.id}")
    )
    assert deleted_sessions == set()

    refresh_response = await admin_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_response.status_code == 401
    assert refresh_response.json()["error"]["code"] == "UNAUTHORIZED"
