# Architecture

## 1. 개요

이 프로젝트는 풀스택 웹 서비스를 빠르게 시작하기 위한 **재사용 가능한 프로젝트 템플릿**입니다.

설치 및 실행 방법은 [README.md](./README.md)를 참조하세요.

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
| | react-hook-form | latest | 폼 상태 관리 + 유효성 검사 |
| | zod | latest | 스키마 기반 폼 유효성 검사 (zodResolver) |
| | openapi-ts | latest | API 클라이언트/타입 자동 생성 |
| **Backend** | FastAPI | 0.115+ | async 기반 |
| | Pydantic | v2 | 데이터 검증 |
| | SQLAlchemy | 2.0+ (async) | ORM |
| **DB** | PostgreSQL | 16+ | asyncpg 드라이버 |
| | Redis | 7+ | redis-py async |
| **인증** | JWT (PyJWT) | 커스텀 | access + refresh token |
| **마이그레이션** | Alembic | latest | autogenerate |
| **테스트** | pytest | latest | Backend TDD (pytest-asyncio) |
| | vitest | latest | Frontend 단위/통합 테스트 (RTL, MSW) |
| | Playwright | latest | Frontend E2E 테스트 |
| **배포** | Docker Compose | latest | 올인원 구성 |
| **CI/CD** | GitHub Actions | - | 자동화 파이프라인 |
| **로깅** | structlog | latest | 구조화 JSON 로깅 (stdlib 통합) |
| **Git Hooks** | pre-commit | latest | 커밋 전 lint/format 자동 실행 |

---

## 3. 디렉토리 구조

```
fullstack-template/
├── infra/                        # PostgreSQL + Redis (docker compose)
│   ├── docker-compose.yml
│   ├── .env.example
│   └── initdb/
├── backend/                      # FastAPI (uv)
│   ├── app/
│   │   ├── api/
│   │   │   ├── dependencies.py
│   │   │   └── v1/
│   │   │       ├── endpoints/
│   │   │       │   ├── auth.py
│   │   │       │   ├── admin_users.py
│   │   │       │   ├── health.py
│   │   │       │   └── users.py
│   │   │       └── router.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── database.py
│   │   │   ├── exceptions.py
│   │   │   ├── logging.py
│   │   │   ├── redis.py
│   │   │   └── security.py
│   │   ├── models/
│   │   │   ├── base.py
│   │   │   └── user.py
│   │   ├── repositories/
│   │   │   └── user_repository.py
│   │   ├── schemas/
│   │   │   ├── auth.py
│   │   │   ├── error.py
│   │   │   └── user.py
│   │   ├── services/
│   │   │   ├── auth_service.py
│   │   │   ├── admin_user_service.py
│   │   │   └── google_oauth_service.py
│   │   └── main.py
│   ├── alembic/
│   ├── tests/
│   ├── pyproject.toml
│   ├── uv.lock
│   └── .env.example
├── frontend/                     # Next.js 15 (pnpm)
│   ├── src/
│   │   ├── app/
│   │   │   ├── (public)/
│   │   │   │   └── login/
│   │   │   │       └── page.tsx
│   │   │   ├── (auth)/
│   │   │   │   ├── layout.tsx
│   │   │   │   ├── dashboard/
│   │   │   │   │   └── page.tsx
│   │   │   │   └── admin/
│   │   │   │       └── users/
│   │   │   │           └── page.tsx
│   │   │   ├── api/
│   │   │   │   ├── auth/
│   │   │   │   │   ├── google/
│   │   │   │   │   │   ├── login/
│   │   │   │   │   │   │   └── route.ts
│   │   │   │   │   │   └── callback/
│   │   │   │   │   │       └── route.ts
│   │   │   │   │   ├── refresh/
│   │   │   │   │   │   └── route.ts
│   │   │   │   │   ├── logout/
│   │   │   │   │   │   └── route.ts
│   │   │   │   │   └── test-login/
│   │   │   │   │       └── route.ts
│   │   │   │   └── [...path]/
│   │   │   │       └── route.ts
│   │   │   ├── globals.css
│   │   │   ├── layout.tsx
│   │   │   └── page.tsx
│   │   ├── client/               # openapi-ts 자동 생성 (수동 수정 금지)
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── lib/
│   │   ├── middleware.ts
│   │   └── tests/
│   ├── e2e/
│   ├── openapi-ts.config.ts
│   ├── package.json
│   ├── pnpm-lock.yaml
│   ├── playwright.config.ts
│   ├── tsconfig.json
│   ├── vitest.config.ts
│   └── .env.example
├── README.md
├── ARCHITECTURE.md
├── AUTH.md
├── CONVENTIONS.md
├── CONVENTIONS-FRONTEND.md
├── CONVENTIONS-BACKEND.md
├── SPECS-BACKEND.md
├── SPECS-FRONTEND.md
└── SPECS-INFRA.md
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

**핵심 동작:** 쿠키에서 access_token 추출 → Authorization 헤더 첨부 → Backend로 프록시.

프록시 구현 코드 및 경로 변환 규칙은 [SPECS-FRONTEND.md §1.1](./SPECS-FRONTEND.md#11-bff-프록시)을 참조하세요.

### 4.2 JWT 인증 흐름

인증/인가의 전체 설계(토큰 구성, Refresh Token Rotation, Replay Detection, 쿠키 전략, 인증 플로우)와 참조 구현은 [AUTH.md](./AUTH.md)를 참조하세요.

### 4.3 에러 핸들링

통합 에러 응답 포맷을 사용합니다.

커스텀 예외 계층(`AppException` 기반)과 통합 에러 JSON 포맷을 사용합니다. 에러 규칙은 [CONVENTIONS-BACKEND.md §5](./CONVENTIONS-BACKEND.md#5-에러-응답-포맷), 구현 코드는 [SPECS-BACKEND.md §1.5](./SPECS-BACKEND.md#15-error-schemas--exception-hierarchy)를 참조하세요. Frontend 에러 처리는 [SPECS-FRONTEND.md §3](./SPECS-FRONTEND.md#3-에러-처리)를 참조하세요.

### 4.4 DB 마이그레이션

Alembic을 사용하여 데이터베이스 스키마를 관리합니다. 모델 규칙은 [CONVENTIONS-BACKEND.md §6](./CONVENTIONS-BACKEND.md#6-db-모델--마이그레이션)를 참조하세요.

**PK 전략:** 모든 테이블은 UUID v4를 Primary Key로 사용합니다 (`uuid.uuid4` default).

마이그레이션 명령어는 [README.md](./README.md#주요-명령어)를 참조하세요.

### 4.5 보안

#### Security Headers

Next.js `next.config.ts`에서 보안 헤더(X-Content-Type-Options, X-Frame-Options, CSP 등)를 설정합니다. FastAPI는 BFF 뒤에 있으므로 브라우저와 직접 통신하지 않아, 보안 헤더는 Next.js에서만 설정합니다. 설정 코드는 [SPECS-INFRA.md §6.1](./SPECS-INFRA.md#61-nextconfigts-보안-헤더)을 참조하세요.

#### CORS (FastAPI)

Backend의 CORS 설정은 `Settings.ALLOWED_ORIGINS`로 관리합니다. BFF 뒤에서 동작하므로 Next.js origin만 허용하며, 운영 환경에서 `["*"]`는 금지입니다. 설정 코드는 [SPECS-BACKEND.md §1.11](./SPECS-BACKEND.md#111-mainpy-전체-참조-구현)의 CORSMiddleware 설정을 참조하세요.

#### CSRF 방어

이 프로젝트는 별도 CSRF 토큰 없이 다중 계층 방어를 사용합니다:

| 방어 계층 | 설명 |
|-----------|------|
| `SameSite=lax` 쿠키 | cross-site POST 요청에 쿠키 미전송 |
| BFF 프록시 | 클라이언트 → Next.js(동일 origin) → Backend |
| CORS | Backend는 허용된 origin만 접근 가능 |
| `Content-Type: application/json` | 단순 form 제출 불가 (CORS preflight 트리거) |

#### Rate Limiting

인증 엔드포인트에 IP 기반 rate limiting을 적용합니다. 적용 대상, 제한 수치, 구현 규칙은 [CONVENTIONS-BACKEND.md §9](./CONVENTIONS-BACKEND.md#9-rate-limiting)를 참조하세요. 구현 코드는 [SPECS-BACKEND.md §1.7](./SPECS-BACKEND.md#17-rate-limiting)을 참조하세요.

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

**Redis 접근 원칙:**
- Refresh Token 관리 등 캐시/세션 작업은 Service 계층에서 Redis에 직접 접근
- Redis 접근 로직이 복잡해지면 별도 Repository로 분리

---

## 6. 개발 환경

로컬 개발은 infra를 컨테이너로 띄우고(POSTGRES/REDIS), Frontend/Backend는 로컬 명령으로 실행합니다.

| 서비스 | 포트 | 비고 |
|--------|------|------|
| frontend | 3000 | `cd frontend && pnpm dev` |
| backend | 8000 | `cd backend && uv run uvicorn app.main:app --reload` |
| db | 5432 | PostgreSQL 16 |
| redis | 6379 | Redis 7 |

infra 실행은 `docker compose -f infra/docker-compose.yml up -d`를 사용합니다.
환경변수는 스택별 `.env.example`를 기준으로 관리합니다: `infra/.env.example`, `backend/.env.example`, `frontend/.env.example`.

---

## 7. 배포

이 템플릿은 로컬 개발에 필요한 `infra/docker-compose.yml`(PostgreSQL/Redis)만 포함합니다.
운영 배포(Dockerfile, reverse proxy, CI/CD 등)는 프로젝트 요구에 맞게 별도로 구성하세요.
