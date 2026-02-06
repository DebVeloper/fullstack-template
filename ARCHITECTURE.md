# Architecture

## 1. 개요

이 프로젝트는 풀스택 웹 서비스를 빠르게 시작하기 위한 **재사용 가능한 프로젝트 템플릿**입니다.

### 사용법

```bash
git clone https://github.com/DebVeloper/fullstack-template.git my-project
cd my-project
# 프로젝트명에 맞게 설정 변경 후 개발 시작
```

### 관련 문서

| 문서 | 설명 |
|------|------|
| [CONVENTIONS.md](./CONVENTIONS.md) | 코딩 컨벤션, API 규격, 테스팅 규격 |
| [AGENTS.md](./AGENTS.md) | AI 에이전트 작업 규칙 |
| [CLAUDE.md](./CLAUDE.md) | Claude Code 프로젝트 설정 |

---

## 2. 기술 스택

| 영역 | 기술 | 버전 | 비고 |
|------|------|------|------|
| **언어** | TypeScript | 5.x (strict mode) | Frontend |
| | Python | 3.12+ | Backend |
| **Frontend** | Next.js | 15 (App Router) | React 19 기반 |
| | TanStack Query | v5 | 서버 상태 관리 |
| | Tailwind CSS | v4 | 유틸리티 퍼스트 |
| | shadcn/ui | latest | 컴포넌트 라이브러리 |
| **Backend** | FastAPI | 0.115+ | async 기반 |
| | Pydantic | v2 | 데이터 검증 |
| | SQLAlchemy | 2.0+ (async) | ORM |
| **DB** | PostgreSQL | 16+ | asyncpg 드라이버 |
| | Redis | 7+ | redis-py async |
| **인증** | JWT | 커스텀 | access + refresh token |
| **마이그레이션** | Alembic | latest | autogenerate |
| **테스트** | pytest | latest | Backend TDD |
| | vitest | latest | Frontend TDD |
| **배포** | Docker Compose | latest | 올인원 구성 |
| **CI/CD** | GitHub Actions | - | 자동화 파이프라인 |

---

## 3. 디렉토리 구조

```
fullstack-template/
├── frontend/                    # Next.js 애플리케이션
│   ├── src/
│   │   ├── app/                 # App Router (라우팅 & 페이지)
│   │   │   ├── (auth)/          # 인증 필요 라우트 그룹
│   │   │   ├── (public)/        # 공개 라우트 그룹
│   │   │   ├── api/             # BFF API Routes (프록시)
│   │   │   ├── layout.tsx       # 루트 레이아웃
│   │   │   └── page.tsx         # 홈페이지
│   │   ├── components/
│   │   │   ├── ui/              # shadcn/ui 기본 컴포넌트
│   │   │   ├── features/        # 비즈니스 로직 컴포넌트
│   │   │   └── layouts/         # 레이아웃 컴포넌트
│   │   ├── hooks/
│   │   │   └── queries/         # TanStack Query 커스텀 훅
│   │   ├── lib/                 # 유틸리티, API 클라이언트
│   │   └── types/               # TypeScript 타입 정의
│   ├── public/                  # 정적 파일
│   ├── next.config.ts
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   ├── vitest.config.ts
│   └── package.json
├── backend/                     # FastAPI 애플리케이션
│   ├── app/
│   │   ├── api/
│   │   │   ├── v1/
│   │   │   │   ├── endpoints/   # API 엔드포인트 모듈
│   │   │   │   │   ├── auth.py
│   │   │   │   │   └── users.py
│   │   │   │   └── router.py    # v1 라우터 집합
│   │   │   └── dependencies.py  # 공유 의존성 (인증 등)
│   │   ├── core/                # 핵심 설정
│   │   │   ├── config.py        # 환경변수 설정
│   │   │   ├── security.py      # JWT, 비밀번호 해싱
│   │   │   ├── database.py      # DB 엔진 & 세션
│   │   │   └── exceptions.py    # 커스텀 예외 계층
│   │   ├── models/              # SQLAlchemy 모델
│   │   │   ├── base.py          # Base, TimestampMixin
│   │   │   └── user.py
│   │   ├── schemas/             # Pydantic 스키마
│   │   │   ├── auth.py
│   │   │   ├── common.py        # PaginatedResponse 등 공통
│   │   │   ├── error.py         # ErrorResponse 스키마
│   │   │   └── user.py
│   │   ├── services/            # 비즈니스 로직 계층
│   │   │   ├── auth_service.py
│   │   │   └── user_service.py
│   │   ├── repositories/        # 데이터 접근 계층
│   │   │   ├── base.py          # BaseRepository 제네릭
│   │   │   └── user_repository.py
│   │   └── main.py              # FastAPI 엔트리포인트
│   ├── alembic/                 # DB 마이그레이션
│   │   ├── versions/
│   │   └── env.py
│   ├── tests/                   # pytest 테스트
│   │   ├── conftest.py
│   │   ├── test_auth.py
│   │   ├── test_users.py
│   │   ├── services/            # 서비스 단위 테스트
│   │   └── repositories/        # 레포지토리 단위 테스트
│   ├── alembic.ini
│   ├── pyproject.toml
│   └── requirements.txt
├── docker/                      # Docker 설정
│   ├── frontend/
│   │   └── Dockerfile
│   └── backend/
│       └── Dockerfile
├── .github/
│   └── workflows/
│       ├── ci.yml               # PR 검증 워크플로우
│       └── cd.yml               # 배포 워크플로우
├── docker-compose.yml           # 개발 환경
├── docker-compose.prod.yml      # 운영 환경
├── .env.example                 # 환경변수 템플릿
├── ARCHITECTURE.md              # 아키텍처 문서 (본 문서)
├── CONVENTIONS.md               # 코딩 컨벤션
└── AGENTS.md                    # AI 에이전트 규칙
```

---

## 4. 아키텍처 패턴

### 4.1 BFF (Backend For Frontend) 패턴

클라이언트는 FastAPI에 직접 접근하지 않고, Next.js API Route를 프록시로 사용합니다.

```
┌──────────┐     ┌──────────────────┐     ┌──────────────┐     ┌────────────┐
│ Browser  │────▶│ Next.js          │────▶│ FastAPI      │────▶│ PostgreSQL │
│          │◀────│ (BFF API Route)  │◀────│ (Backend)    │◀────│ / Redis    │
└──────────┘     └──────────────────┘     └──────────────┘     └────────────┘
                  :3000                    :8000
```

**장점:**
- 클라이언트에 백엔드 URL 노출 방지
- 쿠키/토큰을 서버 사이드에서 안전하게 관리
- 요청/응답 변환 가능 (BFF 역할)
- CORS 이슈 회피

**Next.js API Route 프록시 예시:**

```typescript
// frontend/src/app/api/[...path]/route.ts
import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://backend:8000";

async function proxyRequest(req: NextRequest) {
  const path = req.nextUrl.pathname.replace(/^\/api/, "");
  const url = `${BACKEND_URL}/api/v1${path}${req.nextUrl.search}`;

  const cookieStore = await cookies();
  const accessToken = cookieStore.get("access_token")?.value;

  const headers = new Headers(req.headers);
  headers.delete("host");
  if (accessToken) {
    headers.set("Authorization", `Bearer ${accessToken}`);
  }

  const response = await fetch(url, {
    method: req.method,
    headers,
    body: req.method !== "GET" && req.method !== "HEAD"
      ? await req.text()
      : undefined,
  });

  return new NextResponse(response.body, {
    status: response.status,
    headers: response.headers,
  });
}

export const GET = proxyRequest;
export const POST = proxyRequest;
export const PATCH = proxyRequest;
export const DELETE = proxyRequest;
```

### 4.2 JWT 인증 흐름

**토큰 구성:**

| 토큰 | 형식 | 만료 | 저장소 |
|------|------|------|--------|
| Access Token | JWT (HS256) | 15분 | httpOnly 쿠키 |
| Refresh Token | UUID v4 | 7일 | Redis + httpOnly 쿠키 |

**Refresh Token Rotation:** 갱신 시 기존 refresh token을 폐기하고 새 토큰 발급 (탈취 방어).

**인증 플로우:**

```
1. 로그인
   Client ──POST /api/auth/login──▶ BFF ──▶ FastAPI
                                              │
                                              ├─ 사용자 인증 (bcrypt 비교)
                                              ├─ Access Token 생성 (JWT, 15분)
                                              ├─ Refresh Token 생성 (UUID)
                                              ├─ Redis에 Refresh Token 저장
                                              │
   Client ◀── Set-Cookie(httpOnly) ◀── BFF ◀──┘

2. 인증된 요청
   Client ──GET /api/users/me──▶ BFF ──▶ FastAPI
                                          │
                                          ├─ Authorization 헤더에서 JWT 추출
                                          ├─ JWT 검증 (서명, 만료)
                                          ├─ 사용자 조회
                                          │
   Client ◀── 200 User ◀── BFF ◀─────────┘

3. 토큰 갱신
   Client ──POST /api/auth/refresh──▶ BFF ──▶ FastAPI
                                               │
                                               ├─ Refresh Token 쿠키 추출
                                               ├─ Redis에서 유효성 확인
                                               ├─ 기존 Refresh Token 삭제 (Rotation)
                                               ├─ 새 Access + Refresh Token 생성
                                               ├─ Redis에 새 Refresh Token 저장
                                               │
   Client ◀── Set-Cookie(httpOnly) ◀── BFF ◀──┘

4. 로그아웃
   Client ──POST /api/auth/logout──▶ BFF ──▶ FastAPI
                                              │
                                              ├─ Redis에서 Refresh Token 삭제
                                              │
   Client ◀── Clear-Cookie ◀── BFF ◀─────────┘
```

### 4.3 에러 핸들링

통합 에러 응답 포맷을 사용합니다. 상세 스키마는 [CONVENTIONS.md §3.4](./CONVENTIONS.md#34-에러-응답-포맷)를 참조하세요.

**응답 포맷:**

```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "User not found",
    "details": null
  }
}
```

**커스텀 예외 계층:**

```
AppException (base)
├── BadRequestException     (400)
├── UnauthorizedException   (401)
├── ForbiddenException      (403)
├── NotFoundException       (404)
├── ConflictException       (409)
└── InternalServerException (500)
```

### 4.4 DB 마이그레이션

Alembic을 사용하여 데이터베이스 스키마를 관리합니다. 모델 규칙은 [CONVENTIONS.md §3.5](./CONVENTIONS.md#35-db-모델--마이그레이션)를 참조하세요.

**공통 필드 (TimestampMixin):**

```python
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

**마이그레이션 워크플로우:**

```bash
# 마이그레이션 생성 (autogenerate)
alembic revision --autogenerate -m "add users table"

# 마이그레이션 적용
alembic upgrade head

# 롤백
alembic downgrade -1
```

---

## 5. 데이터 흐름

### 5.1 요청/응답 흐름

```
Browser
  │
  ▼
Next.js (BFF API Route)          ← 쿠키에서 토큰 추출, Authorization 헤더 첨부
  │
  ▼
FastAPI Router                   ← 요청 유효성 검증 (Pydantic), 인증 확인 (Depends)
  │
  ▼
Service Layer                    ← 비즈니스 로직 처리
  │
  ▼
Repository Layer                 ← 데이터 접근 (SQLAlchemy async)
  │
  ▼
PostgreSQL / Redis               ← 데이터 저장소
```

### 5.2 3-Layer 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│ Router (API Layer)                                              │
│  - HTTP 요청/응답 처리                                          │
│  - Pydantic 스키마 검증                                         │
│  - 인증/인가 (Depends)                                          │
│  - 직접 DB 접근 금지                                            │
├─────────────────────────────────────────────────────────────────┤
│ Service (Business Layer)                                        │
│  - 비즈니스 로직                                                │
│  - 트랜잭션 관리                                                │
│  - 여러 Repository 조합                                         │
├─────────────────────────────────────────────────────────────────┤
│ Repository (Data Layer)                                         │
│  - CRUD 연산                                                    │
│  - 쿼리 빌드                                                    │
│  - BaseRepository 상속                                          │
└─────────────────────────────────────────────────────────────────┘
```

---

## 6. 개발 환경

### docker-compose.yml

```yaml
services:
  frontend:
    build:
      context: ./frontend
      dockerfile: ../docker/frontend/Dockerfile
      target: development
    ports:
      - "3000:3000"
    volumes:
      - ./frontend/src:/app/src
    environment:
      - BACKEND_URL=http://backend:8000
    depends_on:
      - backend

  backend:
    build:
      context: ./backend
      dockerfile: ../docker/backend/Dockerfile
      target: development
    ports:
      - "8000:8000"
    volumes:
      - ./backend/app:/app/app
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/app
      - REDIS_URL=redis://redis:6379/0
      - SECRET_KEY=dev-secret-key-change-in-production
      - ACCESS_TOKEN_EXPIRE_MINUTES=15
      - REFRESH_TOKEN_EXPIRE_DAYS=7
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  db:
    image: postgres:16-alpine
    ports:
      - "5432:5432"
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
      - POSTGRES_DB=app
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
  redis_data:
```

### .env.example

```bash
# Backend
DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/app
REDIS_URL=redis://redis:6379/0
SECRET_KEY=your-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# Frontend
BACKEND_URL=http://backend:8000
NEXT_PUBLIC_APP_NAME=MyApp
```

### Hot Reload

| 서비스 | 방식 | 설정 |
|--------|------|------|
| Frontend | Next.js Fast Refresh | `volumes: ./frontend/src:/app/src` |
| Backend | uvicorn `--reload` | `volumes: ./backend/app:/app/app` |

---

## 7. 배포

### Multi-stage Dockerfile 전략

```dockerfile
# docker/backend/Dockerfile
FROM python:3.12-slim AS base
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM base AS development
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

FROM base AS production
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

```dockerfile
# docker/frontend/Dockerfile
FROM node:20-alpine AS base
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM base AS development
COPY . .
CMD ["npm", "run", "dev"]

FROM base AS builder
COPY . .
RUN npm run build

FROM node:20-alpine AS production
WORKDIR /app
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public
CMD ["node", "server.js"]
```

### docker-compose.prod.yml 개요

```yaml
services:
  frontend:
    build:
      context: ./frontend
      dockerfile: ../docker/frontend/Dockerfile
      target: production
    ports:
      - "3000:3000"
    environment:
      - BACKEND_URL=http://backend:8000

  backend:
    build:
      context: ./backend
      dockerfile: ../docker/backend/Dockerfile
      target: production
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - SECRET_KEY=${SECRET_KEY}

  db:
    image: postgres:16-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - POSTGRES_DB=${POSTGRES_DB}

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

### GitHub Actions CI/CD

```yaml
# .github/workflows/ci.yml
name: CI

on:
  pull_request:
    branches: [main, develop]

jobs:
  frontend:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: npm
          cache-dependency-path: frontend/package-lock.json
      - run: npm ci
      - run: npm run lint
      - run: npm run type-check
      - run: npm run test -- --coverage

  backend:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: backend
    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: test
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -r requirements.txt
      - run: ruff check .
      - run: mypy .
      - run: pytest --cov --cov-report=xml
```
