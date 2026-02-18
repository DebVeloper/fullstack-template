from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Annotated

import pytest
from fastapi import APIRouter, Depends, FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.core.security import create_access_token
from app.main import register_exception_handlers
from app.models.user import User

TEST_SECRET = "jwt-test-secret-key-with-at-least-32-bytes"


@pytest.fixture(autouse=True)
def set_secret_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SECRET_KEY", TEST_SECRET)


def create_test_app() -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)

    router = APIRouter()

    @router.get("/me")
    async def me(
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> dict[str, str]:
        return {"user_id": str(current_user.id)}

    app.include_router(router)
    return app


async def build_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    app = create_test_app()

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
async def current_user_client(
    db_session: AsyncSession,
) -> AsyncGenerator[AsyncClient, None]:
    async for client in build_client(db_session):
        yield client


async def test_get_current_user_accepts_valid_bearer_token(
    db_session: AsyncSession,
    current_user_client: AsyncClient,
) -> None:
    user = User(
        google_sub="active-user-sub",
        email="active-user@example.com",
        name="Active User",
        picture_url="https://example.com/active.png",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    token = create_access_token(user.id)

    response = await current_user_client.get(
        "/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json() == {"user_id": str(user.id)}


async def test_get_current_user_rejects_inactive_user(
    db_session: AsyncSession,
    current_user_client: AsyncClient,
) -> None:
    user = User(
        google_sub="inactive-user-sub",
        email="inactive-user@example.com",
        name="Inactive User",
        picture_url="https://example.com/inactive.png",
        is_active=False,
    )
    db_session.add(user)
    await db_session.flush()

    token = create_access_token(user.id)

    response = await current_user_client.get(
        "/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "UNAUTHORIZED"


async def test_get_current_user_rejects_soft_deleted_user(
    db_session: AsyncSession,
    current_user_client: AsyncClient,
) -> None:
    user = User(
        google_sub="deleted-user-sub",
        email="deleted-user@example.com",
        name="Deleted User",
        picture_url="https://example.com/deleted.png",
        is_active=True,
        deleted_at=datetime.now(UTC),
    )
    db_session.add(user)
    await db_session.flush()

    token = create_access_token(user.id)

    response = await current_user_client.get(
        "/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "UNAUTHORIZED"
