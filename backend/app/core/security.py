import os
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from pydantic import ValidationError

from app.core.config import get_settings
from app.core.exceptions import UnauthorizedException
from app.schemas.auth import TokenPayload

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15


def _get_secret_key() -> str:
    secret_key = os.getenv("SECRET_KEY")
    if secret_key:
        return secret_key

    try:
        configured_secret_key = get_settings().SECRET_KEY
    except ValidationError as exc:
        raise RuntimeError("SECRET_KEY environment variable is required") from exc

    if not configured_secret_key:
        raise RuntimeError("SECRET_KEY environment variable is required")

    return configured_secret_key


def create_access_token(user_id: UUID) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "exp": int((now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)).timestamp()),
        "iat": int(now.timestamp()),
        "type": "access",
    }
    return jwt.encode(payload, _get_secret_key(), algorithm=ALGORITHM)


def verify_access_token(token: str) -> TokenPayload:
    try:
        payload = jwt.decode(token, _get_secret_key(), algorithms=[ALGORITHM])
        return TokenPayload.model_validate(payload)
    except (jwt.InvalidTokenError, ValidationError, RuntimeError) as exc:
        raise UnauthorizedException(message="Invalid or expired token") from exc
