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
    # get, get_multi, count, delete도 동일 패턴
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

예외 계층 및 에러 JSON 포맷은 [ARCHITECTURE.md §4.3](./ARCHITECTURE.md#43-에러-핸들링)을 참조하세요.

### 1.6 conftest.py Fixture

```python
# tests/conftest.py
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.database import get_db
from app.main import app
from app.models.base import Base

TEST_DATABASE_URL = settings.DATABASE_URL.replace("/app", "/test")

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
async def client(db_session: AsyncSession):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
async def authenticated_client(client: AsyncClient):
    """로그인된 클라이언트. 테스트 사용자 생성 후 인증 쿠키 설정."""
    # 테스트 사용자 생성 + 로그인 → access_token 쿠키 설정
    # 프로젝트에 맞게 구현
    ...
```

---

## 2. Auth

### 2.1 Security 함수 시그니처

```python
# core/security.py
def create_access_token(user_id: UUID) -> str: ...    # JWT 발급 (HS256, SECRET_KEY)
def create_refresh_token() -> str: ...                 # UUID v4 생성
def verify_access_token(token: str) -> dict: ...       # JWT 검증 (서명 + 만료 + type=="access")
def verify_password(plain: str, hashed: str) -> bool: ...  # bcrypt (passlib)
def hash_password(password: str) -> str: ...           # bcrypt (passlib)
```

### 2.2 인증 의존성

```python
# api/dependencies.py
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

async def get_current_user(
    db: AsyncSession = Depends(get_db),
    token: str = Depends(oauth2_scheme),
) -> User:
    # JWT에서 user_id 추출 → DB 조회 → is_active 확인
    # 실패 시 401 UNAUTHORIZED
```

---

## 3. Pydantic Schemas

### 3.1 Create / Update / Response 패턴

```python
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str

class UserUpdate(BaseModel):
    name: str | None = None
    password: str | None = None

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    email: EmailStr
    name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
```

### 3.2 PaginatedResponse 제네릭

```python
class PaginatedResponse(BaseModel, Generic[T]):
    items: Sequence[T]
    total: int
    page: int
    size: int
    pages: int
```
