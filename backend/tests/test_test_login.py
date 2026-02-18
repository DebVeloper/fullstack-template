import os
from collections.abc import AsyncGenerator, Generator
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.redis import get_redis
from app.main import app
from app.models.user import User
from app.repositories.user_repository import user_repository

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/app",
)
os.environ.setdefault(
    "DATABASE_URL_TEST",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/app",
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("SECRET_KEY", "jwt-test-secret-key-with-at-least-32-bytes")
os.environ.setdefault("ADMIN_EMAIL", "admin@example.com")
os.environ.setdefault("GOOGLE_OAUTH_CLIENT_ID", "test-client-id")
os.environ.setdefault("GOOGLE_OAUTH_CLIENT_SECRET", "test-client-secret")
os.environ.setdefault(
    "GOOGLE_OAUTH_REDIRECT_URI",
    "http://localhost:3000/api/auth/google/callback",
)
os.environ.setdefault("ALLOWED_ORIGINS", "http://localhost:3000")


@pytest.fixture(autouse=True)
def clear_settings_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[None, None, None]:
    monkeypatch.setenv("SECRET_KEY", "jwt-test-secret-key-with-at-least-32-bytes")
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


async def test_test_login_returns_404_when_feature_disabled(
    auth_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AUTH_TEST_MODE", "false")
    monkeypatch.setenv("AUTH_TEST_SECRET", "e2e-secret")

    response = await auth_client.post(
        "/api/v1/auth/test-login",
        json={"email": "e2e-user@example.com", "name": "E2E User"},
        headers={"x-test-auth-secret": "e2e-secret"},
    )

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "NOT_FOUND",
            "message": "Not found",
            "details": None,
        }
    }


async def test_test_login_is_not_exposed_in_openapi_schema(
    auth_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AUTH_TEST_MODE", "true")
    monkeypatch.setenv("AUTH_TEST_SECRET", "e2e-secret")

    response = await auth_client.get("/openapi.json")

    assert response.status_code == 200
    assert "/api/v1/auth/test-login" not in response.json()["paths"]


@pytest.mark.parametrize(
    "provided_secret",
    [None, "wrong-secret"],
)
async def test_test_login_rejects_missing_or_invalid_secret(
    auth_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    provided_secret: str | None,
) -> None:
    monkeypatch.setenv("AUTH_TEST_MODE", "true")
    monkeypatch.setenv("AUTH_TEST_SECRET", "expected-secret")

    headers: dict[str, str] = {}
    if provided_secret is not None:
        headers["x-test-auth-secret"] = provided_secret

    response = await auth_client.post(
        "/api/v1/auth/test-login",
        json={"email": "e2e-user@example.com", "name": "E2E User"},
        headers=headers,
    )

    assert response.status_code == 401
    assert response.json() == {
        "error": {
            "code": "UNAUTHORIZED",
            "message": "Invalid test auth secret",
            "details": None,
        }
    }


async def test_test_login_creates_user_and_returns_token_pair(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    redis_session: Redis,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AUTH_TEST_MODE", "true")
    monkeypatch.setenv("AUTH_TEST_SECRET", "expected-secret")

    response = await auth_client.post(
        "/api/v1/auth/test-login",
        json={"email": "new-e2e-user@example.com", "name": "New E2E User"},
        headers={"x-test-auth-secret": "expected-secret"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["refresh_token"]

    user = await user_repository.get_by_email(db_session, "new-e2e-user@example.com")
    assert user is not None
    assert user.name == "New E2E User"
    assert user.is_active is True
    assert user.deleted_at is None

    refresh_mapping = await redis_session.get(f"refresh_token:{body['refresh_token']}")
    assert refresh_mapping is not None


@pytest.mark.parametrize(
    ("is_active", "deleted_at"),
    [
        (False, None),
        (True, datetime.now(UTC)),
    ],
)
async def test_test_login_rejects_inactive_or_soft_deleted_user(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
    is_active: bool,
    deleted_at: datetime | None,
) -> None:
    monkeypatch.setenv("AUTH_TEST_MODE", "true")
    monkeypatch.setenv("AUTH_TEST_SECRET", "expected-secret")

    user = User(
        google_sub=f"test-login-{uuid4()}",
        email="locked-e2e-user@example.com",
        name="Locked E2E User",
        picture_url=None,
        is_active=is_active,
        deleted_at=deleted_at,
    )
    db_session.add(user)
    await db_session.flush()

    response = await auth_client.post(
        "/api/v1/auth/test-login",
        json={"email": "locked-e2e-user@example.com", "name": "Locked E2E User"},
        headers={"x-test-auth-secret": "expected-secret"},
    )

    assert response.status_code == 401
    assert response.json() == {
        "error": {
            "code": "UNAUTHORIZED",
            "message": "User not found or inactive",
            "details": None,
        }
    }
