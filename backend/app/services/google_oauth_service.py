from typing import Any, TypedDict

import httpx
import jwt

from app.core.config import get_settings
from app.core.exceptions import UnauthorizedException

GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
GOOGLE_JWKS_ENDPOINT = "https://www.googleapis.com/oauth2/v3/certs"
GOOGLE_ID_TOKEN_ALGORITHM = "RS256"
GOOGLE_ISSUERS = ("accounts.google.com", "https://accounts.google.com")
GOOGLE_HTTP_TIMEOUT_SECONDS = 10.0


class GoogleTokenExchangeResult(TypedDict):
    access_token: str
    id_token: str


class GoogleIdTokenClaims(TypedDict):
    sub: str
    email: str
    email_verified: bool
    name: str | None
    picture: str | None


async def exchange_code_for_tokens(
    *,
    code: str,
    code_verifier: str,
) -> GoogleTokenExchangeResult:
    settings = get_settings()
    payload = {
        "code": code,
        "code_verifier": code_verifier,
        "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
        "client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET,
        "redirect_uri": settings.GOOGLE_OAUTH_REDIRECT_URI,
        "grant_type": "authorization_code",
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                GOOGLE_TOKEN_ENDPOINT,
                data=payload,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=GOOGLE_HTTP_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise UnauthorizedException(
            message="Failed to exchange Google authorization code"
        ) from exc

    raw_tokens = response.json()
    if not isinstance(raw_tokens, dict):
        raise UnauthorizedException(message="Google token response is invalid")

    access_token = raw_tokens.get("access_token")
    id_token = raw_tokens.get("id_token")
    if not isinstance(access_token, str) or not isinstance(id_token, str):
        raise UnauthorizedException(message="Google token response is invalid")

    return {
        "access_token": access_token,
        "id_token": id_token,
    }


async def verify_id_token(id_token: str) -> GoogleIdTokenClaims:
    try:
        header = jwt.get_unverified_header(id_token)
    except jwt.InvalidTokenError as exc:
        raise UnauthorizedException(message="Invalid Google id token") from exc

    kid = header.get("kid")
    algorithm = header.get("alg")
    if not isinstance(kid, str) or not kid:
        raise UnauthorizedException(message="Invalid Google id token")
    if algorithm != GOOGLE_ID_TOKEN_ALGORITHM:
        raise UnauthorizedException(message="Invalid Google id token")

    jwk = await _get_google_jwk(kid)
    try:
        verification_key = jwt.PyJWK.from_dict(
            jwk, algorithm=GOOGLE_ID_TOKEN_ALGORITHM
        ).key
    except jwt.PyJWKError as exc:
        raise UnauthorizedException(message="Invalid Google id token") from exc

    settings = get_settings()
    try:
        payload = jwt.decode(
            id_token,
            key=verification_key,
            algorithms=[GOOGLE_ID_TOKEN_ALGORITHM],
            audience=settings.GOOGLE_OAUTH_CLIENT_ID,
            issuer=GOOGLE_ISSUERS,
            options={"require": ["exp", "iss", "aud", "sub"]},
        )
    except jwt.InvalidTokenError as exc:
        raise UnauthorizedException(message="Invalid Google id token") from exc

    return _parse_claims(payload)


async def _get_google_jwk(kid: str) -> dict[str, Any]:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                GOOGLE_JWKS_ENDPOINT,
                timeout=GOOGLE_HTTP_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise UnauthorizedException(message="Failed to load Google JWKS") from exc

    payload = response.json()
    if not isinstance(payload, dict):
        raise UnauthorizedException(message="Failed to load Google JWKS")

    keys = payload.get("keys")
    if not isinstance(keys, list):
        raise UnauthorizedException(message="Failed to load Google JWKS")

    for key in keys:
        if not isinstance(key, dict):
            continue
        key_kid = key.get("kid")
        if key_kid == kid:
            return key

    raise UnauthorizedException(message="Invalid Google id token")


def _parse_claims(payload: Any) -> GoogleIdTokenClaims:
    if not isinstance(payload, dict):
        raise UnauthorizedException(message="Invalid Google id token")

    sub = payload.get("sub")
    email = payload.get("email")
    email_verified = payload.get("email_verified")
    name = payload.get("name")
    picture = payload.get("picture")

    if not isinstance(sub, str) or not sub:
        raise UnauthorizedException(message="Invalid Google id token")
    if not isinstance(email, str) or not email:
        raise UnauthorizedException(message="Invalid Google id token")
    if not isinstance(email_verified, bool):
        raise UnauthorizedException(message="Invalid Google id token")
    if name is not None and not isinstance(name, str):
        raise UnauthorizedException(message="Invalid Google id token")
    if picture is not None and not isinstance(picture, str):
        raise UnauthorizedException(message="Invalid Google id token")

    return {
        "sub": sub,
        "email": email,
        "email_verified": email_verified,
        "name": name,
        "picture": picture,
    }
