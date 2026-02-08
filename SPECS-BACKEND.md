# Backend Reference Specifications

> 이 문서는 Backend에서 사용하는 **참조 구현 코드(보일러플레이트)**를 모아둔 것입니다.
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
from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
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

#### Exception Handlers (main.py)

```python
# main.py exception handlers
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

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

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    # 로깅 (스택트레이스는 서버 로그에만, 클라이언트에는 노출 금지)
    import structlog
    logger = structlog.get_logger()
    logger.exception("unhandled_exception", exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "INTERNAL_ERROR", "message": "Internal server error", "details": None}},
    )
```

예외 계층 및 에러 JSON 포맷은 [ARCHITECTURE.md §4.3](./ARCHITECTURE.md#43-에러-핸들링)을 참조하세요.

### 1.6 conftest.py Fixture

```python
# tests/conftest.py
import pytest
from fakeredis.aioredis import FakeRedis
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.database import get_db
from app.core.redis import get_redis
from app.main import app
from app.models.base import Base

TEST_DATABASE_URL = settings.DATABASE_URL.rsplit("/", 1)[0] + "/test"

engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
async def db_session():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestSessionLocal() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def redis_session():
    """FakeRedis 인스턴스. 실제 Redis 테스트가 필요한 경우 docker-compose의 테스트 Redis 인스턴스 사용."""
    redis = FakeRedis(decode_responses=True)
    try:
        yield redis
    finally:
        await redis.aclose()


@pytest.fixture
async def client(db_session: AsyncSession, redis_session: FakeRedis):
    async def override_get_db():
        yield db_session

    async def override_get_redis():
        yield redis_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
async def authenticated_client(client: AsyncClient, db_session: AsyncSession):
    """로그인된 클라이언트. 테스트 사용자 생성 후 인증 헤더 설정."""
    from app.core.security import hash_password, create_access_token
    from app.models.user import User

    user = User(
        email="test@example.com",
        name="Test User",
        hashed_password=hash_password("testpassword123"),
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)

    access_token = create_access_token(user.id)
    client.headers["Authorization"] = f"Bearer {access_token}"
    yield client
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

```python
# main.py에 추가
from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from app.core.rate_limit import limiter

app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={
            "error": {
                "code": "RATE_LIMIT_EXCEEDED",
                "message": "Too many requests. Please try again later.",
                "details": None,
            }
        },
    )
```

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

```python
# main.py에 추가 (app 생성 직후)
from app.core.logging import configure_logging
from app.core.middleware import RequestIdMiddleware

configure_logging()
app.add_middleware(RequestIdMiddleware)
```

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

from app.api.v1.endpoints import auth, health, users

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
```

---

## 2. Service 계층

### 2.1 UserService 참조 구현

```python
# services/user_service.py
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, NotFoundException, UnauthorizedException
from app.core.security import hash_password, verify_password
from app.models.user import User
from app.repositories.user_repository import user_repository
from app.schemas.user import ChangePasswordRequest, UserCreate, UserUpdate


class UserCreateInternal(BaseModel):
    """password 대신 hashed_password를 포함하는 내부 스키마.
    UserCreate → UserCreateInternal 변환 후 Repository에 전달."""
    email: str
    name: str
    hashed_password: str


async def create_user(db: AsyncSession, *, obj_in: UserCreate) -> User:
    existing = await user_repository.get_by_email(db, email=obj_in.email)
    if existing:
        raise ConflictException(message="Email already registered")
    internal = UserCreateInternal(
        email=obj_in.email,
        name=obj_in.name,
        hashed_password=hash_password(obj_in.password),
    )
    return await user_repository.create(db, obj_in=internal)


async def get_user(db: AsyncSession, *, user_id: UUID) -> User:
    user = await user_repository.get(db, id=user_id)
    if user is None:
        raise NotFoundException(message="User not found")
    return user


async def update_user(db: AsyncSession, *, user_id: UUID, obj_in: UserUpdate) -> User:
    user = await get_user(db, user_id=user_id)
    return await user_repository.update(db, db_obj=user, obj_in=obj_in)


async def change_password(
    db: AsyncSession, *, user_id: UUID, body: ChangePasswordRequest
) -> None:
    """비밀번호 변경. current_password 검증 후 new_password로 업데이트."""
    user = await get_user(db, user_id=user_id)
    if not verify_password(body.current_password, user.hashed_password):
        raise UnauthorizedException(message="Current password is incorrect")
    user.hashed_password = hash_password(body.new_password)
    await db.flush()
    await db.refresh(user)
```

**핵심 원칙:**
- Repository를 조합하여 비즈니스 로직 처리
- 도메인 예외(`ConflictException`, `NotFoundException`)를 발생시켜 Router에 전달
- 트랜잭션 관리는 `get_db()` 컨텍스트에 위임 (Service에서 commit/rollback 호출 금지)

### 2.2 AuthService 참조 구현

```python
# services/auth_service.py
import structlog
from uuid import UUID, uuid4
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import UnauthorizedException
from app.core.security import (
    create_access_token,
    create_refresh_token,
    verify_password,
)
from app.repositories.user_repository import user_repository
from app.schemas.auth import LoginRequest, TokenResponse

logger = structlog.get_logger()

REFRESH_TOKEN_PREFIX = "refresh_token:"
TOKEN_FAMILY_PREFIX = "token_family:"
USER_FAMILIES_PREFIX = "user_families:"


async def login(
    db: AsyncSession, redis: Redis, *, body: LoginRequest
) -> TokenResponse:
    """이메일/비밀번호 인증 → 토큰 발급 + Redis 저장."""
    user = await user_repository.get_by_email(db, email=body.email)
    if user is None or not verify_password(body.password, user.hashed_password):
        logger.info("login_failed", email=body.email, reason="invalid_credentials")
        raise UnauthorizedException(message="Invalid email or password")
    if not user.is_active:
        logger.info("login_failed", email=body.email, reason="inactive_account")
        raise UnauthorizedException(message="User account is inactive")

    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token()
    family_id = str(uuid4())
    ttl = settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400

    pipe = redis.pipeline()
    pipe.set(
        f"{REFRESH_TOKEN_PREFIX}{refresh_token}",
        f"{user.id}:{family_id}",
        ex=ttl,
    )
    pipe.set(f"{TOKEN_FAMILY_PREFIX}{family_id}", refresh_token, ex=ttl)
    pipe.sadd(f"{USER_FAMILIES_PREFIX}{user.id}", family_id)
    await pipe.execute()

    logger.info("login_success", user_id=str(user.id))
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


# 서버리스 환경에서 동시에 여러 인스턴스가 같은 refresh_token으로 요청할 수 있으므로,
# rotation된 구 토큰에 짧은 유예기간(grace period)을 둡니다.
_REFRESH_GRACE_PERIOD_SECONDS = 10

# Refresh Token Rotation Lua 스크립트 — 읽기→판단→쓰기를 하나의 원자적 작업으로 수행
# KEYS[1] = refresh_token:{old_token}
# KEYS[2] = token_family:{family_id}  (family_id는 호출 시점에 알 수 없으므로 스크립트 내부에서 조회)
# ARGV[1] = old_token
# ARGV[2] = new_token
# ARGV[3] = new_refresh_token_key (refresh_token:{new_token})
# ARGV[4] = ttl (seconds)
# ARGV[5] = grace_period (seconds)
# 반환: "OK:{user_id}:{family_id}" | "EXPIRED" | "REPLAY:{user_id}"
_REFRESH_ROTATION_SCRIPT = """
local stored = redis.call('GET', KEYS[1])
if not stored then
    return 'EXPIRED'
end

local sep = stored:find(':[^:]*$')
local user_id = stored:sub(1, sep - 1)
local family_id = stored:sub(sep + 1)
local family_key = 'token_family:' .. family_id

local current_token = redis.call('GET', family_key)
if current_token ~= ARGV[1] then
    return 'REPLAY:' .. user_id
end

-- Rotation: 구 토큰에 grace period TTL 설정, 신규 토큰 저장
redis.call('EXPIRE', KEYS[1], tonumber(ARGV[5]))
redis.call('SET', ARGV[3], user_id .. ':' .. family_id, 'EX', tonumber(ARGV[4]))
redis.call('SET', family_key, ARGV[2], 'EX', tonumber(ARGV[4]))

return 'OK:' .. user_id .. ':' .. family_id
"""


async def refresh(redis: Redis, *, refresh_token: str) -> TokenResponse:
    """Refresh Token Rotation + Replay 감지.
    Lua 스크립트로 원자적 실행하여 race condition 방지."""
    new_refresh_token = create_refresh_token()
    ttl = settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400

    rotation_script = redis.register_script(_REFRESH_ROTATION_SCRIPT)
    result: str = await rotation_script(
        keys=[f"{REFRESH_TOKEN_PREFIX}{refresh_token}"],
        args=[
            refresh_token,
            new_refresh_token,
            f"{REFRESH_TOKEN_PREFIX}{new_refresh_token}",
            ttl,
            _REFRESH_GRACE_PERIOD_SECONDS,
        ],
    )

    if result == "EXPIRED":
        logger.warning("token_replay_suspected", token_prefix=refresh_token[:8])
        raise UnauthorizedException(message="Invalid or expired refresh token")

    if result.startswith("REPLAY:"):
        user_id_str = result.split(":", 1)[1]
        logger.warning("token_replay_detected", user_id=user_id_str)
        await _invalidate_all_sessions(redis, user_id_str)
        raise UnauthorizedException(message="Token reuse detected. All sessions revoked.")

    # result == "OK:{user_id}:{family_id}"
    _, user_id_str, _family_id = result.split(":", 2)
    user_id = UUID(user_id_str)
    new_access_token = create_access_token(user_id)

    logger.info("token_refreshed", user_id=user_id_str)
    return TokenResponse(access_token=new_access_token, refresh_token=new_refresh_token)


async def logout(redis: Redis, *, refresh_token: str) -> None:
    """Redis에서 Refresh Token + Family 삭제."""
    stored = await redis.get(f"{REFRESH_TOKEN_PREFIX}{refresh_token}")
    if stored:
        user_id_str, family_id = stored.rsplit(":", 1)
        pipe = redis.pipeline()
        pipe.delete(f"{REFRESH_TOKEN_PREFIX}{refresh_token}")
        pipe.delete(f"{TOKEN_FAMILY_PREFIX}{family_id}")
        pipe.srem(f"{USER_FAMILIES_PREFIX}{user_id_str}", family_id)
        await pipe.execute()
        logger.info("logout_success", user_id=user_id_str)


_INVALIDATE_ALL_SESSIONS_SCRIPT = """
local family_ids = redis.call('SMEMBERS', KEYS[1])
for _, fid in ipairs(family_ids) do
    local token = redis.call('GET', 'token_family:' .. fid)
    if token then
        redis.call('DEL', 'refresh_token:' .. token)
    end
    redis.call('DEL', 'token_family:' .. fid)
end
redis.call('DEL', KEYS[1])
return #family_ids
"""


async def _invalidate_all_sessions(redis: Redis, user_id: str) -> None:
    """탈취 감지 시 해당 사용자의 모든 세션 무효화. Lua 스크립트로 원자적 실행."""
    invalidate_script = redis.register_script(_INVALIDATE_ALL_SESSIONS_SCRIPT)
    count = await invalidate_script(keys=[f"{USER_FAMILIES_PREFIX}{user_id}"])
    if count:
        logger.warning("all_sessions_invalidated", user_id=user_id, session_count=count)
```

**Refresh Token Rotation + Replay Detection:**
- **Redis Key 구조:**
  - `refresh_token:{token_value}` → value는 `{user_id}:{family_id}`
  - `token_family:{family_id}` → value는 현재 유효한 token_value
  - `user_families:{user_id}` → SET of family_id
- **Replay 감지:** 이미 삭제된 토큰으로 refresh 시도 시 해당 사용자의 모든 세션 무효화
- **TTL:** `REFRESH_TOKEN_EXPIRE_DAYS * 86400` 초

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
from pydantic import BaseModel, EmailStr

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class RefreshRequest(BaseModel):
    refresh_token: str

class TokenPayload(BaseModel):
    sub: str          # user_id (UUID 문자열)
    exp: int          # 만료 시각 (Unix timestamp)
    iat: int          # 발급 시각 (Unix timestamp)
    type: str         # "access"
```

### 3.2 Auth 엔드포인트

```python
# api/v1/endpoints/auth.py
from fastapi import APIRouter, Depends, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.redis import get_redis
from app.schemas.auth import LoginRequest, RefreshRequest, TokenResponse
from app.schemas.user import UserCreate, UserResponse
from app.services import auth_service

router = APIRouter(tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    body: UserCreate,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """회원가입 → 사용자 생성.
    회원가입 후 자동 로그인은 BFF 라우트에서 처리합니다. Backend는 사용자 생성만 담당."""
    from app.services import user_service
    user = await user_service.create_user(db, obj_in=body)
    return user


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> TokenResponse:
    """이메일/비밀번호 인증 → access_token + refresh_token JSON 반환.
    BFF가 쿠키를 설정한다 (Backend는 Set-Cookie 사용 안 함)."""
    return await auth_service.login(db, redis, body=body)

@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    body: RefreshRequest,
    redis: Redis = Depends(get_redis),
) -> TokenResponse:
    """refresh_token을 body로 수신 → 검증 → Rotation(기존 삭제 + 신규 발급)."""
    return await auth_service.refresh(redis, refresh_token=body.refresh_token)

@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    body: RefreshRequest,
    redis: Redis = Depends(get_redis),
) -> None:
    """refresh_token을 body로 수신 → Redis에서 삭제 → 204 No Content."""
    await auth_service.logout(redis, refresh_token=body.refresh_token)
```

### 3.3 Security 함수 구현

```python
# core/security.py
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import jwt
from passlib.context import CryptContext

from app.core.config import settings
from app.schemas.auth import TokenPayload

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"


def create_access_token(user_id: UUID) -> str:
    """JWT access token 발급 (HS256, 15분 만료)"""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        "iat": now,
        "type": "access",
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token() -> str:
    """Refresh token 생성 (UUID v4)"""
    return str(uuid4())


def verify_access_token(token: str) -> TokenPayload:
    """JWT 검증 → TokenPayload 반환 (dict 금지)"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        token_data = TokenPayload(**payload)
        if token_data.type != "access":
            raise ValueError("Invalid token type")
        return token_data
    except (jwt.InvalidTokenError, ValueError) as e:
        from app.core.exceptions import UnauthorizedException
        raise UnauthorizedException(message="Invalid or expired token") from e


def verify_password(plain: str, hashed: str) -> bool:
    """비밀번호 검증 (bcrypt)"""
    return pwd_context.verify(plain, hashed)


def hash_password(password: str) -> str:
    """비밀번호 해싱 (bcrypt)"""
    return pwd_context.hash(password)
```

### 3.4 인증 의존성

```python
# api/dependencies.py
from uuid import UUID

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import UnauthorizedException
from app.core.security import verify_access_token
from app.models.user import User
from app.repositories.user_repository import user_repository

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    token: str = Depends(oauth2_scheme),
) -> User:
    """JWT 검증 → User 조회 → is_active 확인.
    인증 의존성은 횡단 관심사이므로 Service 계층을 경유하지 않고
    Repository를 직접 호출합니다 (CONVENTIONS-BACKEND §1 참조).
    """
    token_data = verify_access_token(token)
    try:
        user_id = UUID(token_data.sub)
    except ValueError as e:
        raise UnauthorizedException(message="Invalid token payload") from e
    user = await user_repository.get(db, id=user_id)
    if user is None or not user.is_active:
        raise UnauthorizedException(message="User not found or inactive")
    return user
```

---

## 4. Pydantic Schemas

### 4.1 Create / Update / Response 패턴

```python
import re
from pydantic import field_validator


def validate_password(password: str) -> str:
    """비밀번호 정책: 8-72자, 소문자/대문자/숫자/특수문자 중 3종 이상."""
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters")
    if len(password) > 72:
        raise ValueError("Password must be at most 72 characters")
    checks = [
        bool(re.search(r"[a-z]", password)),
        bool(re.search(r"[A-Z]", password)),
        bool(re.search(r"\d", password)),
        bool(re.search(r'[!@#$%^&*(),.?":{}|<>]', password)),
    ]
    if sum(checks) < 3:
        raise ValueError(
            "Password must contain at least 3 of: lowercase, uppercase, digit, special character"
        )
    return password


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str

    @field_validator("password")
    @classmethod
    def check_password(cls, v: str) -> str:
        return validate_password(v)


class UserUpdate(BaseModel):
    name: str | None = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def check_new_password(cls, v: str) -> str:
        return validate_password(v)


# api/v1/endpoints/users.py (발췌)
# POST /api/v1/users/me/password — 비밀번호 변경
# current_password 검증 필수, 실패 시 401


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    email: EmailStr
    name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
```

### 4.2 PaginatedResponse 제네릭

```python
class PaginatedResponse(BaseModel, Generic[T]):
    items: Sequence[T]
    total: int
    page: int
    size: int
    pages: int
```
