import os
from collections.abc import AsyncGenerator, Generator
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
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

TEST_SECRET = "jwt-test-secret-key-with-at-least-32-bytes"


@pytest.fixture(autouse=True)
def set_secret_key(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    monkeypatch.setenv("SECRET_KEY", TEST_SECRET)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
async def admin_client(
    db_session: AsyncSession,
) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        yield client

    app.dependency_overrides.clear()


async def create_superadmin_user(db_session: AsyncSession) -> User:
    user = User(
        google_sub=str(uuid4()),
        email=" Admin@Example.com ",
        name="Super Admin",
        picture_url="https://example.com/superadmin.png",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


def auth_headers(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


async def test_superadmin_cannot_be_locked(
    admin_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    superadmin = await create_superadmin_user(db_session)

    response = await admin_client.patch(
        f"/api/v1/admin/users/{superadmin.id}/lock",
        headers=auth_headers(superadmin),
    )

    assert response.status_code == 403
    assert response.json() == {
        "error": {
            "code": "SUPERADMIN_PROTECTED",
            "message": "Superadmin account cannot be modified",
            "details": None,
        }
    }


async def test_superadmin_cannot_be_soft_deleted(
    admin_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    superadmin = await create_superadmin_user(db_session)

    response = await admin_client.delete(
        f"/api/v1/admin/users/{superadmin.id}",
        headers=auth_headers(superadmin),
    )

    assert response.status_code == 403
    assert response.json() == {
        "error": {
            "code": "SUPERADMIN_PROTECTED",
            "message": "Superadmin account cannot be modified",
            "details": None,
        }
    }
