from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest

from app.core.exceptions import UnauthorizedException
from app.core.security import create_access_token, verify_access_token

TEST_SECRET = "jwt-test-secret-key-with-at-least-32-bytes"


def test_create_access_token_and_verify_access_token_round_trip(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SECRET_KEY", TEST_SECRET)
    user_id = uuid4()

    token = create_access_token(user_id)
    payload = verify_access_token(token)

    assert payload.sub == str(user_id)
    assert payload.type == "access"
    assert payload.exp > payload.iat


def test_verify_access_token_rejects_invalid_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SECRET_KEY", TEST_SECRET)

    with pytest.raises(UnauthorizedException):
        verify_access_token("not-a-valid-jwt")


def test_verify_access_token_rejects_wrong_token_type(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SECRET_KEY", TEST_SECRET)
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "sub": str(uuid4()),
            "exp": int((now + timedelta(minutes=15)).timestamp()),
            "iat": int(now.timestamp()),
            "type": "refresh",
        },
        TEST_SECRET,
        algorithm="HS256",
    )

    with pytest.raises(UnauthorizedException):
        verify_access_token(token)
