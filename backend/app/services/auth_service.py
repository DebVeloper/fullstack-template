from inspect import isawaitable
from typing import Any, cast
from uuid import UUID, uuid4

import structlog
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import UnauthorizedException
from app.core.security import create_access_token
from app.models.user import User
from app.repositories.user_repository import user_repository
from app.schemas.auth import TokenResponse
from app.services import google_oauth_service

logger = structlog.get_logger(__name__)

REFRESH_TOKEN_PREFIX = "refresh_token:"
TOKEN_FAMILY_PREFIX = "token_family:"
USER_FAMILIES_PREFIX = "user_families:"
REFRESH_TOKEN_TTL_SECONDS = 7 * 24 * 60 * 60
REFRESH_TOKEN_GRACE_PERIOD_SECONDS = 10
ROTATION_STATUS_EXPIRED = "EXPIRED"
ROTATION_STATUS_GRACE = "GRACE:"
ROTATION_STATUS_REPLAY = "REPLAY:"
ROTATION_STATUS_ROTATED = "ROTATED:"

_REFRESH_ROTATION_LUA = """
local mapping = redis.call('GET', KEYS[1])
if not mapping then
    return 'EXPIRED'
end

local sep = mapping:find(':[^:]*$')
if not sep then
    redis.call('DEL', KEYS[1])
    return 'EXPIRED'
end

local user_id = mapping:sub(1, sep - 1)
local family_id = mapping:sub(sep + 1)
if user_id == '' or family_id == '' then
    redis.call('DEL', KEYS[1])
    return 'EXPIRED'
end

local family_key = 'token_family:' .. family_id
local current_token = redis.call('GET', family_key)
if not current_token then
    redis.call('DEL', KEYS[1])
    return 'EXPIRED'
end

if current_token ~= ARGV[1] then
    local ttl = redis.call('TTL', KEYS[1])
    if ttl > 0 and ttl <= tonumber(ARGV[3]) then
        return 'GRACE:' .. current_token
    end
    return 'REPLAY:' .. user_id
end

redis.call('SET', ARGV[2], mapping, 'EX', tonumber(ARGV[4]))
redis.call('SET', family_key, ARGV[5], 'EX', tonumber(ARGV[4]))
redis.call('EXPIRE', KEYS[1], tonumber(ARGV[3]))

return 'ROTATED:' .. ARGV[5]
"""


def _refresh_token_key(token: str) -> str:
    return f"{REFRESH_TOKEN_PREFIX}{token}"


def _token_family_key(family_id: str) -> str:
    return f"{TOKEN_FAMILY_PREFIX}{family_id}"


def _user_families_key(user_id: str) -> str:
    return f"{USER_FAMILIES_PREFIX}{user_id}"


async def _resolve_redis_result(value: Any) -> Any:
    if isawaitable(value):
        return await value
    return value


def _execute_redis_command(redis: Redis, *args: object) -> Any:
    redis_client: Any = redis
    return redis_client.execute_command(*args)


def _parse_refresh_mapping(mapping: str) -> tuple[str, str]:
    parts = mapping.rsplit(":", 1)
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise UnauthorizedException(message="Invalid or expired refresh token")
    return parts[0], parts[1]


async def refresh(
    db: AsyncSession,
    redis: Redis,
    *,
    refresh_token: str,
) -> TokenResponse:
    refresh_key = _refresh_token_key(refresh_token)
    stored_mapping = await redis.get(refresh_key)
    if stored_mapping is None:
        raise UnauthorizedException(message="Invalid or expired refresh token")

    user_id_str, family_id = _parse_refresh_mapping(stored_mapping)

    try:
        user_id = UUID(user_id_str)
    except ValueError as exc:
        await redis.delete(refresh_key)
        raise UnauthorizedException(message="Invalid or expired refresh token") from exc

    user = await user_repository.get_by_id(db, user_id=user_id)
    if user is None or not user.is_active or user.deleted_at is not None:
        await redis.delete(refresh_key)
        await _invalidate_all_sessions(redis, user_id_str)
        logger.warning("refresh_denied_user_inactive", user_id=user_id_str)
        raise UnauthorizedException(message="User not found or inactive")

    new_refresh_token = str(uuid4())
    result_raw = await _resolve_redis_result(
        _execute_redis_command(
            redis,
            "EVAL",
            _REFRESH_ROTATION_LUA,
            1,
            refresh_key,
            refresh_token,
            _refresh_token_key(new_refresh_token),
            REFRESH_TOKEN_GRACE_PERIOD_SECONDS,
            REFRESH_TOKEN_TTL_SECONDS,
            new_refresh_token,
        )
    )

    if result_raw is None:
        raise UnauthorizedException(message="Invalid or expired refresh token")
    if isinstance(result_raw, bytes):
        result = result_raw.decode("utf-8")
    elif isinstance(result_raw, str):
        result = result_raw
    else:
        result = str(result_raw)

    if result == ROTATION_STATUS_EXPIRED:
        raise UnauthorizedException(message="Invalid or expired refresh token")

    if result.startswith(ROTATION_STATUS_GRACE):
        current_family_token = result.split(":", 1)[1]
        logger.info(
            "refresh_grace_period_reuse",
            user_id=user_id_str,
            family_id=family_id,
        )
        return TokenResponse(
            access_token=create_access_token(user_id),
            refresh_token=current_family_token,
        )

    if result.startswith(ROTATION_STATUS_REPLAY):
        replay_user_id = result.split(":", 1)[1]
        await redis.delete(refresh_key)
        await _invalidate_all_sessions(redis, replay_user_id)
        logger.warning("refresh_replay_detected", user_id=replay_user_id)
        raise UnauthorizedException(
            message="Token reuse detected. All sessions revoked."
        )

    if not result.startswith(ROTATION_STATUS_ROTATED):
        raise UnauthorizedException(message="Invalid or expired refresh token")

    rotated_refresh_token = result.split(":", 1)[1]

    logger.info("refresh_rotated", user_id=user_id_str, family_id=family_id)
    return TokenResponse(
        access_token=create_access_token(user_id),
        refresh_token=rotated_refresh_token,
    )


async def exchange_google_code_for_tokens(
    db: AsyncSession,
    redis: Redis,
    *,
    code: str,
    code_verifier: str,
) -> TokenResponse:
    token_payload = await google_oauth_service.exchange_code_for_tokens(
        code=code,
        code_verifier=code_verifier,
    )
    id_token_claims = await google_oauth_service.verify_id_token(
        token_payload["id_token"]
    )

    if not id_token_claims["email_verified"]:
        raise UnauthorizedException(message="Google account email is not verified")

    existing_user = await user_repository.get_by_google_sub(
        db,
        google_sub=id_token_claims["sub"],
    )
    if existing_user is not None and (
        not existing_user.is_active or existing_user.deleted_at is not None
    ):
        raise UnauthorizedException(message="User not found or inactive")

    user = await user_repository.upsert_google_user(
        db,
        google_sub=id_token_claims["sub"],
        email=id_token_claims["email"],
        name=id_token_claims["name"] or id_token_claims["email"],
        picture_url=id_token_claims["picture"],
    )

    return await issue_refresh_token_pair(redis, user_id=user.id)


async def test_login(
    db: AsyncSession,
    redis: Redis,
    *,
    email: str,
    name: str | None,
) -> TokenResponse:
    user = await user_repository.get_by_email(db, email)

    if user is None:
        user = User(
            google_sub=f"test-login-{uuid4()}",
            email=email,
            name=name or email,
            picture_url=None,
            is_active=True,
        )
        db.add(user)
        await db.flush()
        await db.refresh(user)

    if not user.is_active or user.deleted_at is not None:
        raise UnauthorizedException(message="User not found or inactive")

    if name and user.name != name:
        user.name = name
        await db.flush()

    return await issue_refresh_token_pair(redis, user_id=user.id)


async def logout(redis: Redis, *, refresh_token: str) -> None:
    refresh_key = _refresh_token_key(refresh_token)
    stored_mapping = await redis.get(refresh_key)
    if stored_mapping is None:
        return

    try:
        user_id_str, family_id = _parse_refresh_mapping(stored_mapping)
    except UnauthorizedException:
        await redis.delete(refresh_key)
        return

    family_key = _token_family_key(family_id)
    current_family_token = await redis.get(family_key)

    pipe = redis.pipeline()
    pipe.delete(refresh_key)
    if current_family_token is not None:
        pipe.delete(_refresh_token_key(current_family_token))
    pipe.delete(family_key)
    pipe.srem(_user_families_key(user_id_str), family_id)
    await pipe.execute()

    logger.info("logout_success", user_id=user_id_str, family_id=family_id)


async def issue_refresh_token_pair(
    redis: Redis,
    *,
    user_id: UUID,
) -> TokenResponse:
    refresh_token = str(uuid4())
    family_id = str(uuid4())
    user_id_str = str(user_id)

    pipe = redis.pipeline()
    pipe.set(
        _refresh_token_key(refresh_token),
        f"{user_id_str}:{family_id}",
        ex=REFRESH_TOKEN_TTL_SECONDS,
    )
    pipe.set(
        _token_family_key(family_id),
        refresh_token,
        ex=REFRESH_TOKEN_TTL_SECONDS,
    )
    pipe.sadd(_user_families_key(user_id_str), family_id)
    await pipe.execute()

    return TokenResponse(
        access_token=create_access_token(user_id),
        refresh_token=refresh_token,
    )


async def revoke_all_sessions(redis: Redis, *, user_id: str) -> None:
    await _invalidate_all_sessions(redis, user_id)


async def _invalidate_all_sessions(redis: Redis, user_id: str) -> None:
    family_ids_result = await _resolve_redis_result(
        _execute_redis_command(
            redis,
            "SMEMBERS",
            _user_families_key(user_id),
        )
    )
    if isinstance(family_ids_result, set):
        family_ids = cast(set[str], family_ids_result)
    elif isinstance(family_ids_result, (list, tuple)):
        family_ids = {str(item) for item in family_ids_result}
    elif family_ids_result is None:
        family_ids = set()
    else:
        family_ids = {str(cast(Any, family_ids_result))}

    pipe = redis.pipeline()
    for family_id in family_ids:
        family_key = _token_family_key(family_id)
        current_token = await redis.get(family_key)
        if current_token is not None:
            pipe.delete(_refresh_token_key(current_token))
        pipe.delete(family_key)

    pipe.delete(_user_families_key(user_id))
    await pipe.execute()

    if family_ids:
        logger.warning(
            "refresh_sessions_invalidated",
            user_id=user_id,
            session_count=len(family_ids),
        )
