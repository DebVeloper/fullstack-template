# Backend Reference Specifications

> 이 문서는 Backend에서 사용하는 **참조 구현 코드**를 모아둔 것입니다.
> 규칙과 컨벤션은 [CONVENTIONS-BACKEND.md](./CONVENTIONS-BACKEND.md)를 참조하세요.

---

## 1. Core

### 1.1 BaseRepository

```python
# repositories/base.py
class BaseRepository(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """제네릭 CRUD 레포지토리. get, get_multi, count, create, update, delete 메서드 제공."""

    def __init__(self, model: type[ModelType]) -> None:
        self.model = model

    async def create(self, db: AsyncSession, *, obj_in: CreateSchemaType) -> ModelType:
        db_obj = self.model(**obj_in.model_dump())
        db.add(db_obj)
        await db.flush()       # commit이 아닌 flush — 세션 컨텍스트가 commit 관리
        await db.refresh(db_obj)
        return db_obj

    async def update(self, db: AsyncSession, *, db_obj: ModelType, obj_in: UpdateSchemaType) -> ModelType:
        for field, value in obj_in.model_dump(exclude_unset=True).items():
            setattr(db_obj, field, value)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def get(self, db: AsyncSession, *, id: UUID) -> ModelType | None:
        result = await db.execute(select(self.model).where(self.model.id == id))
        return result.scalar_one_or_none()

    async def get_multi(
        self, db: AsyncSession, *, page: int = 1, size: int = 20,
    ) -> Sequence[ModelType]:
        offset = (page - 1) * size
        result = await db.execute(
            select(self.model).offset(offset).limit(size).order_by(self.model.created_at.desc())
        )
        return result.scalars().all()

    async def count(self, db: AsyncSession) -> int:
        result = await db.execute(select(func.count()).select_from(self.model))
        return result.scalar_one()

    async def delete(self, db: AsyncSession, *, id: UUID) -> bool:
        obj = await self.get(db, id=id)
        if obj is None:
            return False
        await db.delete(obj)
        await db.flush()
        return True
```

### 1.2 Settings

```python
# core/config.py
from pydantic import ConfigDict
from pydantic_settings import BaseSettings  # pydantic-settings 패키지

class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env")

    DATABASE_URL: str
    REDIS_URL: str
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000", "http://frontend:3000"]
    LOG_LEVEL: str = "INFO"
    LOG_JSON: bool = True

settings = Settings()
```

### 1.3 Database Session

```python
# core/database.py
engine = create_async_engine(settings.DATABASE_URL, pool_size=10, max_overflow=20)
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

### 1.4 Base Model + TimestampMixin

```python
# models/base.py
class Base(DeclarativeBase):
    pass

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(),
    )
```

```python
# models/user.py
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    google_sub: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    picture_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
```

### 1.5 Error Schemas + Exception Hierarchy

```python
# schemas/error.py
class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict | list | None = None

class ErrorResponse(BaseModel):
    error: ErrorDetail
```

#### AppException 구현

```python
# core/exceptions.py
class AppException(Exception):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: list | dict | None = None,
    ) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details

class BadRequestException(AppException):
    def __init__(self, message: str = "Bad request", details=None):
        super().__init__(400, "BAD_REQUEST", message, details)

class UnauthorizedException(AppException):
    def __init__(self, message: str = "Unauthorized", details=None):
        super().__init__(401, "UNAUTHORIZED", message, details)

class ForbiddenException(AppException):
    def __init__(self, message: str = "Forbidden", details=None):
        super().__init__(403, "FORBIDDEN", message, details)

class NotFoundException(AppException):
    def __init__(self, message: str = "Not found", details=None):
        super().__init__(404, "NOT_FOUND", message, details)

class ConflictException(AppException):
    def __init__(self, message: str = "Conflict", details=None):
        super().__init__(409, "CONFLICT", message, details)

class InternalServerException(AppException):
    def __init__(self, message: str = "Internal server error", details=None):
        super().__init__(500, "INTERNAL_ERROR", message, details)
```

Exception Handler 등록 코드는 [§1.11 main.py 전체 참조 구현](#111-mainpy-전체-참조-구현)을 참조하세요.
예외 계층 및 에러 JSON 포맷은 [ARCHITECTURE.md §4.3](./ARCHITECTURE.md#43-에러-핸들링)을 참조하세요.

### 1.6 conftest.py Fixture

```python
# tests/conftest.py
import os
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.core.database import get_db
from app.core.redis import get_redis
from app.main import app
from app.models.base import Base
from app.models.user import User  # noqa: F401


class HealthyDBSession:
    async def execute(self, _query: object) -> None:
        return None


class FakeRedis:
    async def ping(self) -> bool:
        return True

    async def aclose(self) -> None:
        return None


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(scope="session")
def test_database_url() -> str:
    database_url_test = os.getenv("DATABASE_URL_TEST")
    if database_url_test is not None:
        return database_url_test

    return get_settings().DATABASE_URL_TEST


@pytest.fixture
async def db_session(test_database_url: str) -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(test_database_url)
    test_session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with test_session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
async def redis_session() -> AsyncGenerator[FakeRedis, None]:
    redis = FakeRedis()
    yield redis
    await redis.aclose()


@pytest.fixture
async def client(redis_session: FakeRedis) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db() -> AsyncGenerator[HealthyDBSession, None]:
        yield HealthyDBSession()

    async def override_get_redis() -> AsyncGenerator[FakeRedis, None]:
        yield redis_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as async_client:
        yield async_client
    app.dependency_overrides.clear()
```

### 1.7 Rate Limiting

```python
# core/rate_limit.py
from slowapi import Limiter

def _get_client_ip(request) -> str:
    """프록시 환경에서 실제 클라이언트 IP 추출."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"

limiter = Limiter(key_func=_get_client_ip)
```

main.py 등록 코드는 [§1.11 main.py 전체 참조 구현](#111-mainpy-전체-참조-구현)을 참조하세요.

```python
# api/v1/endpoints/auth.py에서 사용
from app.core.rate_limit import limiter

@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
async def login(...): ...

@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("10/minute")
async def refresh(...): ...
```

### 1.8 로깅 설정

```python
# core/logging.py
import logging
import structlog
from app.core.config import settings


def configure_logging() -> None:
    """structlog 초기 설정. main.py에서 앱 시작 시 호출."""
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if settings.LOG_JSON:
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer()

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(settings.LOG_LEVEL.upper())
```

```python
# core/middleware.py
import uuid
import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class RequestIdMiddleware(BaseHTTPMiddleware):
    """요청마다 고유 request_id를 생성하고 structlog 컨텍스트에 바인딩."""

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
```

main.py 등록 코드는 [§1.11 main.py 전체 참조 구현](#111-mainpy-전체-참조-구현)을 참조하세요.

### 1.9 Health Check

```python
# api/v1/endpoints/health.py
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.redis import get_redis

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check(
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> JSONResponse:
    """Liveness + Readiness probe. DB와 Redis 연결 상태 확인."""
    db_ok = False
    redis_ok = False
    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        pass
    try:
        await redis.ping()
        redis_ok = True
    except Exception:
        pass

    status = "healthy" if (db_ok and redis_ok) else "unhealthy"
    return JSONResponse(
        status_code=200 if status == "healthy" else 503,
        content={"status": status, "db": db_ok, "redis": redis_ok},
    )
```

### 1.10 UserRepository

```python
# repositories/user_repository.py
from typing import TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.base import BaseRepository
from app.schemas.user import UserCreate, UserUpdate

class UserRepository(BaseRepository[User, UserCreate, UserUpdate]):
    """User 도메인 Repository. BaseRepository 상속 + 커스텀 쿼리 메서드."""

    async def get_by_email(self, db: AsyncSession, *, email: str) -> User | None:
        result = await db.execute(
            select(self.model).where(self.model.email == email)
        )
        return result.scalar_one_or_none()


# 모듈 레벨 싱글턴
user_repository = UserRepository(User)
```

### 1.11 main.py 전체 참조 구현

```python
# main.py
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import AppException
from app.core.logging import configure_logging
from app.core.middleware import RequestIdMiddleware
from app.core.rate_limit import limiter
from app.core.redis import close_redis_pool, init_redis_pool


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 수명주기 관리. startup/shutdown 이벤트 대체."""
    # Startup
    await init_redis_pool()
    yield
    # Shutdown
    await close_redis_pool()


configure_logging()

app = FastAPI(title="App", lifespan=lifespan)

# --- 미들웨어 등록 순서 ---
# 1. CORS (가장 바깥쪽에서 처리)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["*"],
)
# 2. RequestIdMiddleware (요청마다 고유 ID 할당)
app.add_middleware(RequestIdMiddleware)

# --- Rate Limiter ---
app.state.limiter = limiter


# --- Exception Handlers ---
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message, "details": exc.details}},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    details = [
        {"field": ".".join(str(loc) for loc in e["loc"][1:]), "message": e["msg"]}
        for e in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={"error": {"code": "VALIDATION_ERROR", "message": "Request validation failed", "details": details}},
    )


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={"error": {"code": "RATE_LIMIT_EXCEEDED", "message": "Too many requests. Please try again later.", "details": None}},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    import structlog
    logger = structlog.get_logger()
    logger.exception("unhandled_exception", exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "INTERNAL_ERROR", "message": "Internal server error", "details": None}},
    )


# --- Router Mount ---
app.include_router(api_router, prefix="/api/v1")
```

### 1.12 v1/router.py

```python
# api/v1/router.py
from fastapi import APIRouter

from app.api.v1.endpoints import admin_users, auth, health, users

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router, prefix="/auth")
api_router.include_router(users.router, prefix="/users")
api_router.include_router(admin_users.router, prefix="/admin/users")
```

---

## 2. Service 계층

### 2.1 AdminUserService 참조 구현

```python
# services/admin_user_service.py
from datetime import UTC, datetime
from uuid import UUID

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException, NotFoundException
from app.models.user import User
from app.repositories.user_repository import user_repository
from app.services import auth_service

SUPERADMIN_PROTECTED_CODE = "SUPERADMIN_PROTECTED"
SUPERADMIN_PROTECTED_MESSAGE = "Superadmin account cannot be modified"


def normalize_email(email: str) -> str:
    return email.strip().casefold()


def is_superadmin_email(*, user_email: str, admin_email: str) -> bool:
    return normalize_email(user_email) == normalize_email(admin_email)


def _ensure_not_superadmin(*, target_user: User, admin_email: str) -> None:
    if is_superadmin_email(user_email=target_user.email, admin_email=admin_email):
        raise AppException(
            status_code=403,
            code=SUPERADMIN_PROTECTED_CODE,
            message=SUPERADMIN_PROTECTED_MESSAGE,
        )


async def lock_user(
    db: AsyncSession,
    redis: Redis,
    *,
    user_id: UUID,
    admin_email: str,
) -> User:
    user = await user_repository.get_by_id(db, user_id=user_id)
    if user is None:
        raise NotFoundException(message="User not found")

    _ensure_not_superadmin(target_user=user, admin_email=admin_email)

    updated_user = await user_repository.set_active_status(db, user=user, is_active=False)
    await auth_service.revoke_all_sessions(redis, user_id=str(updated_user.id))
    return updated_user
```

**핵심 원칙:**
- Repository를 조합하여 비즈니스 로직 처리
- 도메인 예외(`NotFoundException`, `AppException`)를 발생시켜 Router에 전달
- 계정 상태 변경(lock/delete) 시 세션 패밀리 revoke로 refresh를 즉시 차단
- 트랜잭션 관리는 `get_db()` 컨텍스트에 위임 (Service에서 commit/rollback 호출 금지)

### 2.2 AuthService

auth_service 모듈의 전체 구현은 [§3.3 AuthService](#33-authservice)를 참조하세요.

**핵심 요약:**
- Refresh Token Rotation + Replay Detection (Lua 스크립트로 원자적 실행)
- Token Family 패턴으로 탈취 조기 감지
- Grace Period (10초) — 서버리스 환경 동시 요청 대응
- 탈취 감지 시 해당 사용자의 모든 세션 무효화

### 2.3 Redis 의존성

```python
# core/redis.py
from collections.abc import AsyncGenerator

from redis.asyncio import ConnectionPool, Redis

from app.core.config import settings

pool: ConnectionPool | None = None


async def init_redis_pool() -> None:
    """Redis 커넥션 풀 초기화. main.py lifespan startup에서 호출."""
    global pool
    pool = ConnectionPool.from_url(settings.REDIS_URL, decode_responses=True)


async def close_redis_pool() -> None:
    """Redis 커넥션 풀 종료. main.py lifespan shutdown에서 호출."""
    global pool
    if pool:
        await pool.aclose()
        pool = None


async def get_redis() -> AsyncGenerator[Redis, None]:
    """요청 스코프 Redis 클라이언트. ConnectionPool을 공유하여 매 요청마다 새 연결을 생성하지 않음."""
    assert pool is not None, "Redis pool not initialized. Call init_redis_pool() first."
    redis = Redis(connection_pool=pool)
    try:
        yield redis
    finally:
        await redis.aclose()
```

---

## 3. Auth

### 3.1 Auth 스키마

```python
# schemas/auth.py
from typing import Literal

from pydantic import BaseModel


class RefreshRequest(BaseModel):
    refresh_token: str


class GoogleExchangeRequest(BaseModel):
    code: str
    code_verifier: str


class TestLoginRequest(BaseModel):
    email: str
    name: str | None = None

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"

class TokenPayload(BaseModel):
    sub: str          # user_id (UUID 문자열)
    exp: int          # 만료 시각 (Unix timestamp)
    iat: int          # 발급 시각 (Unix timestamp)
    type: Literal["access"]
```

### 3.2 Security 함수

```python
# core/security.py
import os
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from pydantic import ValidationError

from app.core.exceptions import UnauthorizedException
from app.schemas.auth import TokenPayload

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15


def _get_secret_key() -> str:
    secret_key = os.getenv("SECRET_KEY")
    if not secret_key:
        raise RuntimeError("SECRET_KEY environment variable is required")
    return secret_key


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
```

### 3.3 AuthService

Token Rotation, Replay Detection, Grace Period의 설계 전략은 [AUTH.md §4](./AUTH.md#4-refresh-token-rotation--replay-detection)를 참조하세요.

```python
# services/auth_service.py
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
        raise UnauthorizedException(message="Token reuse detected. All sessions revoked.")

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
    id_token_claims = await google_oauth_service.verify_id_token(token_payload["id_token"])

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
```

### 3.4 인증 의존성

```python
# api/dependencies.py
from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.exceptions import ForbiddenException, UnauthorizedException
from app.core.security import verify_access_token
from app.models.user import User
from app.repositories.user_repository import user_repository

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def normalize_email(email: str) -> str:
    return email.strip().casefold()


def is_admin_email(*, user_email: str, admin_email: str) -> bool:
    return normalize_email(user_email) == normalize_email(admin_email)


@dataclass(slots=True)
class AdminPrincipal:
    user: User
    admin_email: str


async def get_current_user(
    db: Annotated[AsyncSession, Depends(get_db)],
    token: Annotated[str, Depends(oauth2_scheme)],
) -> User:
    token_payload = verify_access_token(token)

    try:
        user_id = UUID(token_payload.sub)
    except ValueError as exc:
        raise UnauthorizedException(message="Invalid token payload") from exc

    user = await user_repository.get_by_id(db, user_id=user_id)
    if user is None or not user.is_active or user.deleted_at is not None:
        raise UnauthorizedException(message="User not found or inactive")

    return user


async def require_admin(
    current_user: Annotated[User, Depends(get_current_user)],
) -> AdminPrincipal:
    admin_email = get_settings().ADMIN_EMAIL
    if not is_admin_email(user_email=current_user.email, admin_email=admin_email):
        raise ForbiddenException(message="Admin access required")

    return AdminPrincipal(user=current_user, admin_email=admin_email)
```

### 3.5 Auth 엔드포인트

```python
# api/v1/endpoints/auth.py
from secrets import compare_digest
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Response, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.exceptions import NotFoundException, UnauthorizedException
from app.core.redis import get_redis
from app.schemas.auth import (
    GoogleExchangeRequest,
    RefreshRequest,
    TestLoginRequest,
    TokenResponse,
)
from app.services import auth_service

router = APIRouter(tags=["auth"])


@router.post("/refresh", response_model=TokenResponse)
async def refresh_tokens(
    body: RefreshRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> TokenResponse:
    return await auth_service.refresh(db, redis, refresh_token=body.refresh_token)


@router.post("/google/exchange", response_model=TokenResponse)
async def exchange_google_code(
    body: GoogleExchangeRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> TokenResponse:
    return await auth_service.exchange_google_code_for_tokens(
        db,
        redis,
        code=body.code,
        code_verifier=body.code_verifier,
    )


@router.post("/test-login", response_model=TokenResponse, include_in_schema=False)
async def test_login(
    body: TestLoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
    x_test_auth_secret: Annotated[str | None, Header()] = None,
) -> TokenResponse:
    settings = get_settings()

    if not settings.AUTH_TEST_MODE:
        raise NotFoundException()

    configured_secret = settings.AUTH_TEST_SECRET
    if (
        configured_secret is None
        or x_test_auth_secret is None
        or not compare_digest(x_test_auth_secret, configured_secret)
    ):
        raise UnauthorizedException(message="Invalid test auth secret")

    return await auth_service.test_login(
        db,
        redis,
        email=str(body.email),
        name=body.name,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    body: RefreshRequest,
    redis: Annotated[Redis, Depends(get_redis)],
) -> Response:
    await auth_service.logout(redis, refresh_token=body.refresh_token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
```

**인증 규칙:**
- `OAuth2PasswordBearer` + `Depends`로 인증 주입
- 인증 실패 시 401 `UNAUTHORIZED` 반환
- 3-Layer 예외 규칙(인증 의존성의 Repository 직접 호출)은 [CONVENTIONS-BACKEND.md §1](./CONVENTIONS-BACKEND.md#1-3-layer-구조)을 참조
- 토큰 구성 및 흐름은 [AUTH.md §1-5](./AUTH.md)를 참조

### 3.6 Users Router 참조 구현

```python
# api/v1/endpoints/users.py
from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_user
from app.core.config import get_settings
from app.models.user import User
from app.schemas.user import UserMeResponse

router = APIRouter(tags=["users"])


def normalize_email(email: str) -> str:
    return email.strip().casefold()


def is_admin_email(*, user_email: str, admin_email: str) -> bool:
    return normalize_email(user_email) == normalize_email(admin_email)


@router.get("/me", response_model=UserMeResponse)
async def get_me(
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserMeResponse:
    is_admin = is_admin_email(
        user_email=current_user.email,
        admin_email=get_settings().ADMIN_EMAIL,
    )
    return UserMeResponse(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        picture_url=current_user.picture_url,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at,
        is_admin=is_admin,
    )
```

**핵심:**
- 모든 엔드포인트는 `Depends(get_current_user)`로 인증 필수
- `GET /api/v1/users/me`는 `is_admin`을 포함하여 반환 (`ADMIN_EMAIL` 기반)

---

## 4. Pydantic Schemas

### 4.1 User Schemas

```python
# schemas/user.py
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserMeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    name: str
    picture_url: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    is_admin: bool


class AdminUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    name: str
    picture_url: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class AdminUserListResponse(BaseModel):
    items: list[AdminUserResponse]
    total: int
    page: int
    size: int
    pages: int
```

---

## 5. 로깅 참조

> 로깅 규칙과 금지 사항은 [CONVENTIONS-BACKEND.md §10](./CONVENTIONS-BACKEND.md#10-로깅-전략)을 참조하세요.

### 5.1 로그 포맷 예시

```json
{
  "event": "login_success",
  "level": "info",
  "timestamp": "2024-01-15T10:30:45.123Z",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "request_id": "abc123",
  "ip": "192.168.1.100"
}
```

### 5.2 주요 로깅 지점

| 이벤트 | 레벨 | 필수 필드 |
|--------|------|----------|
| 로그인 성공 | INFO | `user_id` |
| 로그인 실패 | INFO | `email`, `reason` (invalid_credentials/inactive_account) |
| 토큰 갱신 | INFO | `user_id` |
| Replay 토큰 의심 | WARNING | `token_prefix` (앞 8자) |
| Replay 토큰 확정 | WARNING | `user_id`, `family_id` |
| 전체 세션 무효화 | WARNING | `user_id` |
| Rate limit 초과 | WARNING | `ip`, `endpoint` |
| API 요청 | INFO | `method`, `path`, `status_code`, `duration` |
| 예외 발생 | ERROR | `exception`, `traceback` |
