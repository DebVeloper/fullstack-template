import os
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from inspect import isawaitable
from types import SimpleNamespace

import httpx
import pytest
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

import app.services.google_oauth_service as google_oauth_service
from app.core.database import get_db
from app.core.redis import get_redis
from app.core.security import verify_access_token
from app.main import app
from app.models.user import User
from app.repositories.user_repository import user_repository
from app.services.auth_service import (
    REFRESH_TOKEN_PREFIX,
    TOKEN_FAMILY_PREFIX,
    USER_FAMILIES_PREFIX,
)

TEST_SECRET = "jwt-test-secret-key-with-at-least-32-bytes"


async def resolve_redis_result(value: object) -> object:
    if isawaitable(value):
        return await value
    return value


class FakeGoogleTokenResponse:
    def __init__(self, payload: dict[str, str], status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            request = httpx.Request("POST", "https://oauth2.googleapis.com/token")
            response = httpx.Response(self.status_code, request=request)
            raise httpx.HTTPStatusError(
                "google token exchange failed",
                request=request,
                response=response,
            )

    def json(self) -> dict[str, str]:
        return self._payload


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


async def test_exchange_code_for_tokens_uses_settings_redirect_uri(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_request: dict[str, object] = {}

    monkeypatch.setattr(
        google_oauth_service,
        "get_settings",
        lambda: SimpleNamespace(
            GOOGLE_OAUTH_CLIENT_ID="client-id",
            GOOGLE_OAUTH_CLIENT_SECRET="client-secret",
            GOOGLE_OAUTH_REDIRECT_URI="https://frontend.example.com/api/auth/google/callback",
        ),
    )

    async def fake_post(
        self: httpx.AsyncClient,
        url: str,
        *,
        data: dict[str, str],
        headers: dict[str, str],
        timeout: float,
    ) -> FakeGoogleTokenResponse:
        captured_request["url"] = url
        captured_request["data"] = data
        captured_request["headers"] = headers
        captured_request["timeout"] = timeout
        return FakeGoogleTokenResponse(
            {
                "access_token": "google-access-token",
                "id_token": "google-id-token",
            }
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    token_payload = await google_oauth_service.exchange_code_for_tokens(
        code="auth-code-123",
        code_verifier="verifier-abc",
    )

    assert captured_request["url"] == "https://oauth2.googleapis.com/token"
    assert captured_request["data"] == {
        "code": "auth-code-123",
        "code_verifier": "verifier-abc",
        "client_id": "client-id",
        "client_secret": "client-secret",
        "redirect_uri": "https://frontend.example.com/api/auth/google/callback",
        "grant_type": "authorization_code",
    }
    assert captured_request["headers"] == {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    assert captured_request["timeout"] == 10.0
    assert token_payload["access_token"] == "google-access-token"
    assert token_payload["id_token"] == "google-id-token"


async def test_google_exchange_creates_user_issues_tokens_and_stores_refresh_family(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    redis_session: Redis,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_exchange_code_for_tokens(
        *,
        code: str,
        code_verifier: str,
    ) -> dict[str, str]:
        assert code == "auth-code"
        assert code_verifier == "pkce-verifier"
        return {
            "access_token": "google-access",
            "id_token": "google-id-token",
        }

    async def fake_verify_id_token(id_token: str) -> dict[str, object]:
        assert id_token == "google-id-token"
        return {
            "sub": "google-sub-1",
            "email": "first@example.com",
            "name": "First User",
            "picture": "https://example.com/first.png",
            "email_verified": True,
        }

    monkeypatch.setattr(
        google_oauth_service,
        "exchange_code_for_tokens",
        fake_exchange_code_for_tokens,
    )
    monkeypatch.setattr(
        google_oauth_service,
        "verify_id_token",
        fake_verify_id_token,
    )

    response = await auth_client.post(
        "/api/v1/auth/google/exchange",
        json={"code": "auth-code", "code_verifier": "pkce-verifier"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"

    user = await user_repository.get_by_google_sub(
        db_session, google_sub="google-sub-1"
    )
    assert user is not None
    assert user.email == "first@example.com"
    assert user.name == "First User"
    assert user.picture_url == "https://example.com/first.png"

    token_payload = verify_access_token(body["access_token"])
    assert token_payload.sub == str(user.id)

    refresh_mapping = await redis_session.get(
        f"{REFRESH_TOKEN_PREFIX}{body['refresh_token']}"
    )
    assert refresh_mapping is not None
    mapping_user_id, family_id = refresh_mapping.rsplit(":", 1)
    assert mapping_user_id == str(user.id)

    assert (
        await redis_session.get(f"{TOKEN_FAMILY_PREFIX}{family_id}")
        == body["refresh_token"]
    )
    families = await resolve_redis_result(
        redis_session.smembers(f"{USER_FAMILIES_PREFIX}{user.id}")
    )
    assert isinstance(families, set)
    assert family_id in families


async def test_google_exchange_updates_existing_user_by_google_sub(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    existing_user = User(
        google_sub="google-sub-existing",
        email="old@example.com",
        name="Old Name",
        picture_url="https://example.com/old.png",
        is_active=True,
    )
    db_session.add(existing_user)
    await db_session.flush()

    async def fake_exchange_code_for_tokens(
        *,
        code: str,
        code_verifier: str,
    ) -> dict[str, str]:
        assert code == "update-code"
        assert code_verifier == "update-verifier"
        return {
            "access_token": "google-access",
            "id_token": "google-id-token",
        }

    async def fake_verify_id_token(_id_token: str) -> dict[str, object]:
        return {
            "sub": "google-sub-existing",
            "email": "new@example.com",
            "name": "New Name",
            "picture": "https://example.com/new.png",
            "email_verified": True,
        }

    monkeypatch.setattr(
        google_oauth_service,
        "exchange_code_for_tokens",
        fake_exchange_code_for_tokens,
    )
    monkeypatch.setattr(
        google_oauth_service,
        "verify_id_token",
        fake_verify_id_token,
    )

    response = await auth_client.post(
        "/api/v1/auth/google/exchange",
        json={"code": "update-code", "code_verifier": "update-verifier"},
    )

    assert response.status_code == 200

    await db_session.refresh(existing_user)
    assert existing_user.email == "new@example.com"
    assert existing_user.name == "New Name"
    assert existing_user.picture_url == "https://example.com/new.png"

    token_payload = verify_access_token(response.json()["access_token"])
    assert token_payload.sub == str(existing_user.id)


async def test_google_exchange_rejects_unverified_google_email(
    auth_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_exchange_code_for_tokens(
        *,
        code: str,
        code_verifier: str,
    ) -> dict[str, str]:
        assert code == "unverified-code"
        assert code_verifier == "unverified-verifier"
        return {
            "access_token": "google-access",
            "id_token": "google-id-token",
        }

    async def fake_verify_id_token(_id_token: str) -> dict[str, object]:
        return {
            "sub": "google-sub-unverified",
            "email": "unverified@example.com",
            "name": "Unverified",
            "picture": "https://example.com/unverified.png",
            "email_verified": False,
        }

    monkeypatch.setattr(
        google_oauth_service,
        "exchange_code_for_tokens",
        fake_exchange_code_for_tokens,
    )
    monkeypatch.setattr(
        google_oauth_service,
        "verify_id_token",
        fake_verify_id_token,
    )

    response = await auth_client.post(
        "/api/v1/auth/google/exchange",
        json={"code": "unverified-code", "code_verifier": "unverified-verifier"},
    )

    assert response.status_code == 401
    assert response.json() == {
        "error": {
            "code": "UNAUTHORIZED",
            "message": "Google account email is not verified",
            "details": None,
        }
    }


@pytest.mark.parametrize(
    ("is_active", "deleted_at"),
    [
        (False, None),
        (True, datetime.now(UTC)),
    ],
)
async def test_google_exchange_rejects_inactive_or_deleted_user(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    redis_session: Redis,
    monkeypatch: pytest.MonkeyPatch,
    is_active: bool,
    deleted_at: datetime | None,
) -> None:
    existing_user = User(
        google_sub="google-sub-locked",
        email="locked@example.com",
        name="Inactive User",
        picture_url="https://example.com/locked.png",
        is_active=is_active,
        deleted_at=deleted_at,
    )
    db_session.add(existing_user)
    await db_session.flush()

    async def fake_exchange_code_for_tokens(
        *,
        code: str,
        code_verifier: str,
    ) -> dict[str, str]:
        assert code == "locked-code"
        assert code_verifier == "locked-verifier"
        return {
            "access_token": "google-access",
            "id_token": "google-id-token",
        }

    async def fake_verify_id_token(_id_token: str) -> dict[str, object]:
        return {
            "sub": "google-sub-locked",
            "email": "locked@example.com",
            "name": "Inactive User",
            "picture": "https://example.com/locked.png",
            "email_verified": True,
        }

    monkeypatch.setattr(
        google_oauth_service,
        "exchange_code_for_tokens",
        fake_exchange_code_for_tokens,
    )
    monkeypatch.setattr(
        google_oauth_service,
        "verify_id_token",
        fake_verify_id_token,
    )

    response = await auth_client.post(
        "/api/v1/auth/google/exchange",
        json={"code": "locked-code", "code_verifier": "locked-verifier"},
    )

    assert response.status_code == 401
    assert response.json() == {
        "error": {
            "code": "UNAUTHORIZED",
            "message": "User not found or inactive",
            "details": None,
        }
    }
    assert await redis_session.dbsize() == 0
