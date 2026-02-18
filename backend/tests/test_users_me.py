from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from httpx import AsyncClient

import app.api.v1.endpoints.users as users_endpoint
from app.api.dependencies import get_current_user
from app.core.exceptions import UnauthorizedException
from app.main import app
from app.models.user import User


async def test_get_users_me_returns_current_user_with_is_admin_true(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        users_endpoint,
        "get_settings",
        lambda: SimpleNamespace(ADMIN_EMAIL="  ADMIN@example.com  "),
    )

    now = datetime.now(UTC)
    user_id = uuid4()
    user = User(
        id=user_id,
        google_sub="admin-user-sub",
        email="admin@EXAMPLE.com",
        name="Admin User",
        picture_url="https://example.com/admin.png",
        is_active=True,
        created_at=now,
        updated_at=now,
    )

    async def override_get_current_user() -> User:
        return user

    app.dependency_overrides[get_current_user] = override_get_current_user
    response = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": "Bearer test-token"},
    )
    app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(user_id)
    assert body["email"] == "admin@EXAMPLE.com"
    assert body["name"] == "Admin User"
    assert body["picture_url"] == "https://example.com/admin.png"
    assert body["is_active"] is True
    assert body["is_admin"] is True
    assert "created_at" in body
    assert "updated_at" in body


async def test_get_users_me_returns_current_user_with_is_admin_false(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        users_endpoint,
        "get_settings",
        lambda: SimpleNamespace(ADMIN_EMAIL="admin@example.com"),
    )

    now = datetime.now(UTC)
    user = User(
        id=uuid4(),
        google_sub="normal-user-sub",
        email="member@example.com",
        name="Normal User",
        picture_url="https://example.com/member.png",
        is_active=True,
        created_at=now,
        updated_at=now,
    )

    async def override_get_current_user() -> User:
        return user

    app.dependency_overrides[get_current_user] = override_get_current_user
    response = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": "Bearer test-token"},
    )
    app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "member@example.com"
    assert body["is_admin"] is False


async def test_get_users_me_returns_unified_error_envelope_when_dependency_raises(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        users_endpoint,
        "get_settings",
        lambda: SimpleNamespace(ADMIN_EMAIL="admin@example.com"),
    )

    async def override_get_current_user() -> User:
        raise UnauthorizedException(message="Invalid or expired token")

    app.dependency_overrides[get_current_user] = override_get_current_user
    response = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": "Bearer invalid.token.value"},
    )
    app.dependency_overrides.clear()

    assert response.status_code == 401
    assert response.json() == {
        "error": {
            "code": "UNAUTHORIZED",
            "message": "Invalid or expired token",
            "details": None,
        }
    }
