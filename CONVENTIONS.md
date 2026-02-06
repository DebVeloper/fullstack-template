# Conventions

## 1. 프로젝트 컨벤션

### 1.1 네이밍 규칙

| 대상 | 규칙 | 예시 |
|------|------|------|
| 파일 (FE) | kebab-case | `user-profile.tsx` |
| 파일 (BE) | snake_case | `user_service.py` |
| 디렉토리 | kebab-case (FE), snake_case (BE) | `features/`, `user_repository/` |
| React 컴포넌트 | PascalCase | `UserProfile` |
| React 훅 | camelCase, `use` prefix | `useUserQuery` |
| TS 함수/변수 | camelCase | `getUserById` |
| TS 타입/인터페이스 | PascalCase | `UserResponse` |
| Python 함수/변수 | snake_case | `get_user_by_id` |
| Python 클래스 | PascalCase | `UserService` |
| DB 테이블 | snake_case, 복수형 | `users`, `refresh_tokens` |
| DB 컬럼 | snake_case | `created_at`, `is_active` |
| API 경로 | kebab-case, 복수형 명사 | `/api/v1/users`, `/api/v1/auth/login` |
| 환경변수 | UPPER_SNAKE_CASE | `DATABASE_URL`, `SECRET_KEY` |
| FE 공개 환경변수 | `NEXT_PUBLIC_` prefix | `NEXT_PUBLIC_APP_NAME` |
| Git 브랜치 | kebab-case | `feature/user-auth`, `fix/login-bug` |

### 1.2 코드 스타일

**Frontend (ESLint + Prettier):**

```json
// .prettierrc
{
  "semi": true,
  "singleQuote": false,
  "tabWidth": 2,
  "trailingComma": "all",
  "printWidth": 80
}
```

- TypeScript strict mode 필수
- ESLint: `next/core-web-vitals`, `next/typescript`
- 절대 경로 import (`@/` prefix)

**Backend (Ruff + mypy):**

```toml
# pyproject.toml
[tool.ruff]
target-version = "py312"
line-length = 88

[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "UP", "B", "A", "SIM"]

[tool.ruff.lint.isort]
known-first-party = ["app"]

[tool.mypy]
python_version = "3.12"
strict = true
plugins = ["pydantic.mypy"]

[tool.mypy.plugins.pydantic-mypy]
init_forbid_extra = true
init_typed = true
warn_required_dynamic_aliases = true
```

### 1.3 Git 전략

**브랜치 구조:**

```
main ← 운영 배포 브랜치
└── develop ← 개발 통합 브랜치
    ├── feature/user-auth
    ├── feature/dashboard
    ├── fix/login-redirect
    └── hotfix/security-patch (main에서 분기)
```

**Conventional Commits:**

```
type(scope): description

# type: feat, fix, docs, style, refactor, test, chore, ci
# scope: frontend, backend, auth, users, db, docker, ci

# 예시
feat(backend): add user registration endpoint
fix(frontend): resolve login redirect loop
docs: update ARCHITECTURE.md with BFF diagram
test(backend): add auth service unit tests
chore(docker): update postgres to 16.2
```

---

## 2. Frontend 규격

### 2.1 App Router 구조

```
src/app/
├── (auth)/                      # 인증 필요 라우트 그룹
│   ├── layout.tsx               # 인증 체크 레이아웃
│   ├── dashboard/
│   │   └── page.tsx
│   └── settings/
│       └── page.tsx
├── (public)/                    # 공개 라우트 그룹
│   ├── layout.tsx
│   ├── login/
│   │   └── page.tsx
│   └── register/
│       └── page.tsx
├── api/                         # BFF API Routes
│   └── [...path]/
│       └── route.ts
├── layout.tsx                   # 루트 레이아웃 (Providers)
├── page.tsx                     # 홈페이지
├── loading.tsx                  # 글로벌 로딩
├── error.tsx                    # 글로벌 에러
└── not-found.tsx                # 404
```

**파일 컨벤션:**

| 파일 | 용도 |
|------|------|
| `layout.tsx` | 공유 레이아웃 (자식 라우트 유지) |
| `page.tsx` | 라우트 UI |
| `loading.tsx` | Suspense 폴백 (Skeleton UI) |
| `error.tsx` | Error Boundary (`'use client'` 필수) |
| `not-found.tsx` | 404 페이지 |

**Server / Client Component 전략:**

| 기준 | Server Component | Client Component |
|------|-----------------|------------------|
| 데이터 페칭 | O | X (TanStack Query 사용 시 예외) |
| 상태 관리 | X | O |
| 이벤트 핸들러 | X | O |
| 브라우저 API | X | O |
| 기본값 | O (default) | `'use client'` 명시 필요 |

**원칙:** Server Component를 기본으로, `'use client'`는 필요한 최소 범위에만 적용.

### 2.2 컴포넌트 분류

| 디렉토리 | 역할 | 예시 |
|----------|------|------|
| `components/ui/` | shadcn/ui 기본 컴포넌트 | `button.tsx`, `input.tsx`, `dialog.tsx` |
| `components/features/` | 비즈니스 로직 컴포넌트 | `login-form.tsx`, `user-table.tsx` |
| `components/layouts/` | 레이아웃 컴포넌트 | `header.tsx`, `sidebar.tsx`, `footer.tsx` |

**규칙:**
- `ui/`: shadcn/ui CLI로만 추가, 직접 수정 최소화
- `features/`: 도메인별 하위 디렉토리 가능 (`features/auth/`, `features/users/`)
- 컴포넌트 하나당 파일 하나
- 컴포넌트 파일명은 kebab-case, export는 PascalCase

### 2.3 TanStack Query 패턴

**Query Key Factory:**

```typescript
// hooks/queries/keys.ts
export const userKeys = {
  all: ["users"] as const,
  lists: () => [...userKeys.all, "list"] as const,
  list: (params: UserListParams) => [...userKeys.lists(), params] as const,
  details: () => [...userKeys.all, "detail"] as const,
  detail: (id: string) => [...userKeys.details(), id] as const,
};
```

**Custom Hook 캡슐화:**

```typescript
// hooks/queries/use-users.ts
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { userKeys } from "./keys";
import { getUsers, getUser, createUser } from "@/lib/api/users";

export function useUsers(params: UserListParams) {
  return useQuery({
    queryKey: userKeys.list(params),
    queryFn: () => getUsers(params),
  });
}

export function useUser(id: string) {
  return useQuery({
    queryKey: userKeys.detail(id),
    queryFn: () => getUser(id),
    enabled: !!id,
  });
}

export function useCreateUser() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: createUser,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: userKeys.lists() });
    },
  });
}
```

**규칙:**
- 컴포넌트에서 `useQuery`/`useMutation` 직접 호출 금지 → 반드시 커스텀 훅으로 캡슐화
- Query key는 반드시 factory 패턴 사용
- Mutation 성공 시 관련 query invalidation 필수

### 2.4 Tailwind CSS

**shadcn/ui 테마 (CSS 변수):**

```css
/* globals.css */
@layer base {
  :root {
    --background: 0 0% 100%;
    --foreground: 0 0% 3.9%;
    --primary: 0 0% 9%;
    --primary-foreground: 0 0% 98%;
    /* ... shadcn/ui 기본 테마 변수 */
  }

  .dark {
    --background: 0 0% 3.9%;
    --foreground: 0 0% 98%;
    --primary: 0 0% 98%;
    --primary-foreground: 0 0% 9%;
  }
}
```

**cn() 유틸리티:**

```typescript
// lib/utils.ts
import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

**규칙:**
- 인라인 `style` 속성 사용 금지 → Tailwind 클래스 사용
- 조건부 클래스는 `cn()` 유틸리티 사용
- 반응형 디자인은 mobile-first (`sm:`, `md:`, `lg:`)
- 다크모드는 CSS 변수 기반 (`dark:` 클래스)

### 2.5 에러/로딩 처리

**loading.tsx (Skeleton):**

```tsx
// app/(auth)/dashboard/loading.tsx
import { Skeleton } from "@/components/ui/skeleton";

export default function DashboardLoading() {
  return (
    <div className="space-y-4">
      <Skeleton className="h-8 w-48" />
      <div className="grid grid-cols-3 gap-4">
        <Skeleton className="h-32" />
        <Skeleton className="h-32" />
        <Skeleton className="h-32" />
      </div>
    </div>
  );
}
```

**error.tsx:**

```tsx
// app/(auth)/dashboard/error.tsx
"use client";

import { Button } from "@/components/ui/button";

export default function DashboardError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-4 py-16">
      <h2 className="text-lg font-semibold">문제가 발생했습니다</h2>
      <p className="text-sm text-muted-foreground">{error.message}</p>
      <Button onClick={reset}>다시 시도</Button>
    </div>
  );
}
```

**Toast (Sonner):**

```tsx
import { toast } from "sonner";

// 성공
toast.success("저장되었습니다");

// 에러
toast.error("저장에 실패했습니다");
```

---

## 3. Backend 규격

### 3.1 3-Layer 구조

Router(HTTP) → Service(비즈니스) → Repository(데이터) 계층을 엄격히 분리합니다. 디렉토리 구조는 [ARCHITECTURE.md §3](./ARCHITECTURE.md#3-디렉토리-구조)을 참조하세요.

**BaseRepository 패턴:**

```python
# repositories/base.py
from typing import Generic, TypeVar, Type, Optional, Sequence
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.models.base import Base

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class BaseRepository(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """제네릭 CRUD 레포지토리."""

    def __init__(self, model: type[ModelType]) -> None:
        self.model = model

    async def get(self, db: AsyncSession, id: int) -> ModelType | None:
        result = await db.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalars().first()

    async def get_multi(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 20,
    ) -> Sequence[ModelType]:
        result = await db.execute(
            select(self.model).offset(skip).limit(limit)
        )
        return result.scalars().all()

    async def count(self, db: AsyncSession) -> int:
        result = await db.execute(
            select(func.count()).select_from(self.model)
        )
        return result.scalar_one()

    async def create(
        self, db: AsyncSession, *, obj_in: CreateSchemaType
    ) -> ModelType:
        db_obj = self.model(**obj_in.model_dump())
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: ModelType,
        obj_in: UpdateSchemaType,
    ) -> ModelType:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def delete(self, db: AsyncSession, *, id: int) -> bool:
        obj = await self.get(db, id)
        if obj:
            await db.delete(obj)
            return True
        return False
```

**UserRepository 확장:**

```python
# repositories/user_repository.py
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.base import BaseRepository
from app.schemas.user import UserCreate, UserUpdate


class UserRepository(BaseRepository[User, UserCreate, UserUpdate]):
    async def get_by_email(
        self, db: AsyncSession, *, email: str
    ) -> User | None:
        result = await db.execute(
            select(User).where(User.email == email)
        )
        return result.scalars().first()


user_repository = UserRepository(User)
```

### 3.2 Pydantic 스키마

Create / Update / Response 스키마를 분리합니다.

```python
# schemas/user.py
from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str


class UserUpdate(BaseModel):
    name: str | None = None
    password: str | None = None


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
```

**PaginatedResponse 제네릭:**

```python
# schemas/common.py
from typing import Generic, TypeVar, Sequence
from pydantic import BaseModel

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    items: Sequence[T]
    total: int
    page: int
    size: int
    pages: int
```

**규칙:**
- `model_config = ConfigDict(from_attributes=True)` 사용 (Response 스키마)
- `.model_dump()` 사용 (`.dict()` 금지)
- `.model_validate()` 사용 (`.from_orm()` 금지)
- `Optional[X]` 대신 `X | None` 사용 (Python 3.12+)

### 3.3 JWT 인증 상세

인증 흐름은 [ARCHITECTURE.md §4.2](./ARCHITECTURE.md#42-jwt-인증-흐름)를 참조하세요.

**토큰 구조:**

```python
# Access Token Payload
{
    "sub": 123,          # user_id
    "exp": 1700000000,   # 만료 시간 (15분)
    "iat": 1699999100,   # 발급 시간
    "type": "access"
}

# Refresh Token: UUID v4 문자열 (Redis key로 사용)
# Redis key: "refresh_token:{token_uuid}" → value: user_id
# TTL: 7일
```

**security.py:**

```python
# core/security.py
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"


def create_access_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {
        "sub": user_id,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access",
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token() -> str:
    return str(uuid4())


def verify_access_token(token: str) -> dict:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)
```

**dependencies.py:**

```python
# api/dependencies.py
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import verify_access_token
from app.repositories.user_repository import user_repository

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    token: str = Depends(oauth2_scheme),
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = verify_access_token(token)
        user_id: int = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = await user_repository.get(db, user_id)
    if user is None:
        raise credentials_exception
    return user
```

### 3.4 에러 응답 포맷

**ErrorResponse 스키마:**

```python
# schemas/error.py
from pydantic import BaseModel


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict | list | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail
```

**커스텀 예외 계층:**

```python
# core/exceptions.py
from fastapi import HTTPException


class AppException(HTTPException):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: dict | list | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.details = details
        super().__init__(status_code=status_code, detail=message)


class BadRequestException(AppException):
    def __init__(self, message: str = "Bad request", **kwargs):
        super().__init__(400, "BAD_REQUEST", message, **kwargs)


class UnauthorizedException(AppException):
    def __init__(self, message: str = "Unauthorized", **kwargs):
        super().__init__(401, "UNAUTHORIZED", message, **kwargs)


class ForbiddenException(AppException):
    def __init__(self, message: str = "Forbidden", **kwargs):
        super().__init__(403, "FORBIDDEN", message, **kwargs)


class NotFoundException(AppException):
    def __init__(self, message: str = "Not found", **kwargs):
        super().__init__(404, "NOT_FOUND", message, **kwargs)


class ConflictException(AppException):
    def __init__(self, message: str = "Conflict", **kwargs):
        super().__init__(409, "CONFLICT", message, **kwargs)


class InternalServerException(AppException):
    def __init__(self, message: str = "Internal server error", **kwargs):
        super().__init__(500, "INTERNAL_SERVER_ERROR", message, **kwargs)
```

**Exception Handler 등록:**

```python
# main.py (발췌)
from fastapi import Request
from fastapi.responses import JSONResponse
from app.core.exceptions import AppException


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
            }
        },
    )
```

### 3.5 DB 모델 / 마이그레이션

**Base 모델 (TimestampMixin):**

```python
# models/base.py
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
```

**User 모델 예시:**

```python
# models/user.py
from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
```

**Alembic 규칙:**
- 마이그레이션은 항상 `--autogenerate`로 생성
- 수동 수정이 필요한 경우 주석으로 사유 기록
- 마이그레이션 파일에 의미 있는 메시지 작성
- 운영 DB에 `downgrade` 금지

---

## 4. API 규격

### 4.1 RESTful 설계

| 메서드 | 용도 | 예시 |
|--------|------|------|
| `GET` | 리소스 조회 | `GET /api/v1/users` |
| `POST` | 리소스 생성 | `POST /api/v1/users` |
| `PATCH` | 리소스 부분 수정 | `PATCH /api/v1/users/{id}` |
| `DELETE` | 리소스 삭제 | `DELETE /api/v1/users/{id}` |

**규칙:**
- 복수형 명사 사용 (`/users`, `/posts`)
- `PUT` 미사용 → `PATCH`만 사용 (부분 업데이트)
- 중첩 리소스는 최대 2단계 (`/users/{id}/posts`)

### 4.2 버전 관리

- URL 기반 버전: `/api/v1/`
- 라우터 등록: `app.include_router(api_router, prefix="/api/v1")`

### 4.3 응답 포맷

**단일 리소스:**

```json
{
  "id": 1,
  "email": "user@example.com",
  "name": "홍길동",
  "is_active": true,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

**페이지네이션 리스트:**

```json
{
  "items": [
    { "id": 1, "email": "user@example.com", "name": "홍길동" }
  ],
  "total": 42,
  "page": 1,
  "size": 20,
  "pages": 3
}
```

**에러:**

```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "User not found",
    "details": null
  }
}
```

### 4.4 페이지네이션 / 필터링

**페이지네이션 (offset-based):**

| 파라미터 | 타입 | 기본값 | 설명 |
|----------|------|--------|------|
| `page` | int | 1 | 현재 페이지 (1-based) |
| `size` | int | 20 | 페이지당 항목 수 (max: 100) |

**정렬:**

| 파라미터 | 타입 | 기본값 | 설명 |
|----------|------|--------|------|
| `sort_by` | string | `created_at` | 정렬 기준 필드 |
| `order` | string | `desc` | `asc` 또는 `desc` |

**필터링:**
- Query parameter 기반: `GET /api/v1/users?is_active=true&name=홍`
- 검색: `GET /api/v1/users?q=홍길동` (전체 텍스트 검색)

---

## 5. 테스팅 규격

### 5.1 TDD 워크플로우

모든 기능 개발은 반드시 **Red → Green → Refactor** 사이클을 따릅니다.

```
1. Red    — 실패하는 테스트 먼저 작성
2. Green  — 테스트를 통과하는 최소한의 코드 작성
3. Refactor — 코드 정리 (테스트는 계속 통과해야 함)
```

**테스트 없는 기능은 미완성입니다.**

### 5.2 pytest (Backend)

**conftest.py:**

```python
# tests/conftest.py
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.database import get_db
from app.main import app
from app.models.base import Base

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def db_session():
    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def client(db_session: AsyncSession):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client

    app.dependency_overrides.clear()
```

**디렉토리 구조:**

```
tests/
├── conftest.py              # 공유 fixture
├── test_auth.py             # 인증 테스트
├── test_users.py            # 사용자 테스트
├── services/
│   └── test_user_service.py # 서비스 단위 테스트
└── repositories/
    └── test_user_repo.py    # 레포지토리 단위 테스트
```

**네이밍 규칙:**
- 파일: `test_{module}.py`
- 함수: `test_{action}_{condition}_{expected}` (예: `test_create_user_with_valid_data_returns_201`)
- fixture: 명사형 (`db_session`, `authenticated_client`)

### 5.3 vitest + React Testing Library (Frontend)

**설정:**

```typescript
// vitest.config.ts
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    setupFiles: ["./src/tests/setup.ts"],
    globals: true,
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
});
```

**Wrapper fixture (QueryClientProvider):**

```typescript
// src/tests/setup.ts
import "@testing-library/jest-dom/vitest";

// src/tests/utils.tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, type RenderOptions } from "@testing-library/react";
import { type ReactElement } from "react";

function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
}

export function renderWithProviders(
  ui: ReactElement,
  options?: Omit<RenderOptions, "wrapper">,
) {
  const queryClient = createTestQueryClient();

  function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    );
  }

  return render(ui, { wrapper: Wrapper, ...options });
}
```

**LoginForm 테스트 예시:**

```typescript
// components/features/auth/__tests__/login-form.test.tsx
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { renderWithProviders } from "@/tests/utils";
import { LoginForm } from "../login-form";

const server = setupServer(
  http.post("/api/auth/login", async ({ request }) => {
    const body = await request.json();
    if (body.email === "test@example.com") {
      return HttpResponse.json({ message: "OK" });
    }
    return HttpResponse.json(
      { error: { code: "UNAUTHORIZED", message: "Invalid credentials" } },
      { status: 401 },
    );
  }),
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe("LoginForm", () => {
  it("renders email and password fields", () => {
    renderWithProviders(<LoginForm />);

    expect(screen.getByLabelText(/이메일/)).toBeInTheDocument();
    expect(screen.getByLabelText(/비밀번호/)).toBeInTheDocument();
  });

  it("shows validation error for empty fields", async () => {
    const user = userEvent.setup();
    renderWithProviders(<LoginForm />);

    await user.click(screen.getByRole("button", { name: /로그인/ }));

    expect(await screen.findByText(/이메일을 입력해주세요/)).toBeInTheDocument();
  });

  it("submits form with valid data", async () => {
    const user = userEvent.setup();
    renderWithProviders(<LoginForm />);

    await user.type(screen.getByLabelText(/이메일/), "test@example.com");
    await user.type(screen.getByLabelText(/비밀번호/), "password123");
    await user.click(screen.getByRole("button", { name: /로그인/ }));

    // 성공 후 동작 검증
  });
});
```

**규칙:**
- 사용자 행동 기반 테스트 (`getByRole`, `getByLabelText`) — `getByTestId` 최후 수단
- API 모킹은 MSW 사용
- 각 테스트는 독립적 (공유 상태 금지)

### 5.4 커버리지 기준

| 영역 | 최소 커버리지 |
|------|-------------|
| Backend Services | 90% |
| Backend Repositories | 80% |
| Backend API Endpoints | 85% |
| Frontend Hooks (queries) | 80% |
| Frontend Components (features) | 75% |
| Frontend Components (ui) | 측정 제외 (shadcn) |

---

## 6. 환경 & 설정

### 환경변수 네이밍

| 규칙 | 예시 |
|------|------|
| UPPER_SNAKE_CASE | `DATABASE_URL`, `SECRET_KEY` |
| Frontend 공개 변수: `NEXT_PUBLIC_` prefix | `NEXT_PUBLIC_APP_NAME` |
| Boolean 값: `true` / `false` 문자열 | `DEBUG=true` |

### Docker 설정

| 환경 | 파일 | 특징 |
|------|------|------|
| Development | `docker-compose.yml` | Hot reload, 소스 마운트, 디버그 포트 |
| Production | `docker-compose.prod.yml` | Multi-stage 빌드, 최적화 이미지 |

### 시크릿 관리

| 환경 | 방식 |
|------|------|
| 로컬 개발 | `.env` 파일 (`.gitignore`에 등록) |
| CI/CD | GitHub Secrets |
| 운영 | 환경변수 주입 (Docker / 클라우드 시크릿) |

**`.env` 파일은 절대 커밋하지 않습니다.** `.env.example`만 커밋합니다.
