# Architecture

## 1. 개요

이 프로젝트는 풀스택 웹 서비스를 빠르게 시작하기 위한 **재사용 가능한 프로젝트 템플릿**입니다.

### Quick Start

```bash
# 1. 프로젝트 클론
git clone https://github.com/debveloper/fullstack-template.git my-project
cd my-project

# 2. 환경변수 설정
cp .env.example .env
# .env 파일을 열어 SECRET_KEY 등 필수 값 설정

# 3. 개발 환경 실행
docker compose up -d

# 4. DB 마이그레이션
docker compose exec backend alembic upgrade head

# 5. 접속 확인
# Frontend: http://localhost:3000
# Backend API 문서: http://localhost:8000/docs
# PostgreSQL: localhost:5432
# Redis: localhost:6379
```

**주요 명령어:**

| 명령어 | 설명 |
|--------|------|
| `docker compose up -d` | 전체 서비스 시작 |
| `docker compose down` | 전체 서비스 중지 |
| `docker compose logs -f backend` | Backend 로그 확인 |
| `docker compose exec backend alembic revision --autogenerate -m "msg"` | DB 마이그레이션 생성 |
| `docker compose exec backend pytest` | Backend 테스트 실행 |
| `docker compose exec frontend npm test` | Frontend 테스트 실행 |
| `docker compose exec frontend npx playwright test` | E2E 테스트 실행 |
| `docker compose exec frontend npm run generate:api` | openapi-ts 타입 재생성 |

### 관련 문서

| 문서 | 설명 |
|------|------|
| [CONVENTIONS.md](./CONVENTIONS.md) | 공통 컨벤션 (네이밍, Git, API 규격, 테스팅 원칙) |
| [CONVENTIONS-FRONTEND.md](./CONVENTIONS-FRONTEND.md) | Frontend 규격 (App Router, TanStack Query, Tailwind) |
| [CONVENTIONS-BACKEND.md](./CONVENTIONS-BACKEND.md) | Backend 규격 (3-Layer, Pydantic, JWT, DB) |
| [SPECS-BACKEND.md](./SPECS-BACKEND.md) | Backend 참조 구현 코드 (보일러플레이트) |
| [SPECS-FRONTEND.md](./SPECS-FRONTEND.md) | Frontend 참조 구현 코드 (보일러플레이트) |
| [CLAUDE.md](./CLAUDE.md) | Claude Code 프로젝트 설정 및 AI 에이전트 규칙 |

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
| | openapi-ts | latest | API 클라이언트/타입 자동 생성 |
| **Backend** | FastAPI | 0.115+ | async 기반 |
| | Pydantic | v2 | 데이터 검증 |
| | SQLAlchemy | 2.0+ (async) | ORM |
| **DB** | PostgreSQL | 16+ | asyncpg 드라이버 |
| | Redis | 7+ | redis-py async |
| **인증** | JWT | 커스텀 | access + refresh token |
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
│   │   ├── client/              # openapi-ts 자동 생성 (수동 수정 금지)
│   │   ├── types/               # TypeScript 타입 정의
│   │   └── middleware.ts        # 인증 라우트 보호 미들웨어
│   ├── e2e/                     # Playwright E2E 테스트
│   ├── public/                  # 정적 파일
│   ├── next.config.ts
│   ├── tsconfig.json
│   ├── vitest.config.ts
│   ├── playwright.config.ts
│   ├── openapi-ts.config.ts
│   └── package.json
├── backend/                     # FastAPI 애플리케이션
│   ├── app/
│   │   ├── api/
│   │   │   ├── v1/
│   │   │   │   ├── endpoints/   # API 엔드포인트 모듈
│   │   │   │   │   ├── auth.py
│   │   │   │   │   ├── health.py
│   │   │   │   │   └── users.py
│   │   │   │   └── router.py    # v1 라우터 집합
│   │   │   └── dependencies.py  # 공유 의존성 (인증 등)
│   │   ├── core/                # 핵심 설정
│   │   │   ├── config.py        # 환경변수 설정
│   │   │   ├── security.py      # JWT, 비밀번호 해싱
│   │   │   ├── database.py      # DB 엔진 & 세션
│   │   │   ├── redis.py         # Redis 연결 & 세션
│   │   │   ├── exceptions.py    # 커스텀 예외 계층
│   │   │   ├── rate_limit.py    # Rate Limiting (slowapi)
│   │   │   ├── logging.py       # structlog 초기 설정
│   │   │   └── middleware.py    # RequestIdMiddleware
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
├── .pre-commit-config.yaml      # pre-commit 설정
├── ARCHITECTURE.md              # 아키텍처 문서 (본 문서)
├── CONVENTIONS.md               # 공통 컨벤션
├── CONVENTIONS-FRONTEND.md      # Frontend 규격
├── CONVENTIONS-BACKEND.md       # Backend 규격
├── SPECS-BACKEND.md             # Backend 참조 구현 코드
├── SPECS-FRONTEND.md            # Frontend 참조 구현 코드
└── CLAUDE.md                    # Claude Code 설정 및 AI 에이전트 규칙
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

**토큰 구성:**

| 토큰 | 형식 | 만료 | 저장소 |
|------|------|------|--------|
| Access Token | JWT (HS256) | 15분 | httpOnly 쿠키 |
| Refresh Token | UUID v4 | 7일 | Redis + httpOnly 쿠키 |

**Refresh Token Rotation:** 갱신 시 기존 refresh token을 폐기하고 새 토큰 발급 (탈취 방어).

**Refresh Token Replay 감지:**

Token Family 패턴으로 토큰 탈취를 조기 감지합니다.

**Token Family 전략:**
- 각 로그인 세션마다 고유 `family_id` 할당 (UUID v4)
- Redis에 family별 현재 유효 토큰 추적
- Rotation 시 family는 유지하고 토큰만 교체

**Redis Key 구조:**

| Key 패턴 | Value | TTL | 용도 |
|----------|-------|-----|------|
| `refresh_token:{token}` | `{user_id}:{family_id}` | 7일 | 토큰 → 사용자/패밀리 매핑 |
| `token_family:{family_id}` | 현재 유효한 token | 7일 | 패밀리별 최신 토큰 추적 |
| `user_families:{user_id}` | SET of family_id | 무제한 | 사용자의 모든 세션 추적 |

**Replay 감지 시나리오:**

| 상황 | 판단 | Backend 동작 |
|------|------|-------------|
| 토큰이 Redis에 없음 | 이미 rotation됨 또는 만료 | 로그 기록, 401 반환 |
| 토큰은 있지만 family의 현재 토큰과 불일치 | **탈취 확정** — 정상 사용자는 새 토큰을 받았는데 구 토큰이 재사용됨 | 해당 사용자의 **모든 세션 무효화** (user_families의 모든 family 삭제) → 401 + "Token reuse detected. All sessions revoked." |
| 토큰과 family 토큰이 일치 | 정상 요청 | Rotation 수행 (기존 삭제 → 신규 발급) |

**참조 구현:** [SPECS-BACKEND.md §2.2](./SPECS-BACKEND.md#22-authservice-참조-구현)

**쿠키 전략 — BFF 주도 설정:**

Backend는 JSON body로 토큰을 반환하고, BFF(Next.js API Route)가 쿠키를 설정합니다. Backend auth 엔드포인트는 `Set-Cookie` 헤더를 사용하지 않습니다.

| 쿠키 | 값 | httpOnly | secure | sameSite | path | maxAge |
|------|-----|----------|--------|----------|------|--------|
| `access_token` | JWT 문자열 | true | true (prod) | lax | `/` | 15분 (900초) |
| `refresh_token` | UUID v4 | true | true (prod) | lax | `/api/auth` | 7일 (604800초) |

- **Backend 응답**: `TokenResponse { access_token, refresh_token, token_type }` (JSON body)
- **BFF 역할**: Backend 응답 수신 → `Set-Cookie` 헤더로 httpOnly 쿠키 설정 → 클라이언트에 전달
- **Logout**: BFF가 쿠키 삭제 (`maxAge=0`) + Backend에 refresh_token body 전송 → Redis 삭제

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
                                       │        │
                                       │        ├─ Body에서 refresh_token 추출
                                       │        ├─ Redis에서 유효성 확인
                                       │        ├─ 기존 Refresh Token 삭제 (Rotation)
                                       │        ├─ 새 Access + Refresh Token 생성
                                       │        ├─ Redis에 새 Refresh Token 저장
                                       │        │
   Client ◀── Set-Cookie(httpOnly) ◀── BFF ◀──┘
                                       │
                                       └─ 쿠키에서 refresh_token 추출 → Body로 Backend에 전달

4. 로그아웃
   Client ──POST /api/auth/logout──▶ BFF ──▶ FastAPI
                                              │
                                              ├─ Redis에서 Refresh Token 삭제
                                              │
   Client ◀── Clear-Cookie ◀── BFF ◀─────────┘
```

### 4.3 에러 핸들링

통합 에러 응답 포맷을 사용합니다. 상세 스키마는 [SPECS-BACKEND.md §1.5](./SPECS-BACKEND.md#15-error-schemas--exception-hierarchy)를 참조하세요.

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

**422 Validation Error 응답:**

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": [
      { "field": "email", "message": "value is not a valid email address" },
      { "field": "password", "message": "String should have at least 8 characters" }
    ]
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

Alembic을 사용하여 데이터베이스 스키마를 관리합니다. 모델 규칙은 [CONVENTIONS-BACKEND.md §6](./CONVENTIONS-BACKEND.md#6-db-모델--마이그레이션)를 참조하세요.

**PK 전략:** 모든 테이블은 UUID v4를 Primary Key로 사용합니다 (`uuid.uuid4` default).

**마이그레이션 워크플로우:**

```bash
# 마이그레이션 생성 (autogenerate)
alembic revision --autogenerate -m "add users table"

# 마이그레이션 적용
alembic upgrade head

# 롤백
alembic downgrade -1
```

### 4.5 보안

#### Security Headers

Next.js `next.config.ts`에서 보안 헤더를 설정합니다. FastAPI는 BFF 뒤에 있으므로 브라우저와 직접 통신하지 않아, 보안 헤더는 Next.js에서만 설정합니다.

| 헤더 | 값 | 목적 |
|------|-----|------|
| `X-Content-Type-Options` | `nosniff` | MIME 스니핑 방지 |
| `X-Frame-Options` | `DENY` | Clickjacking 방지 |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Referer 정보 제한 |
| `Permissions-Policy` | `camera=(), microphone=(), geolocation=()` | 불필요한 브라우저 API 차단 |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` | HTTPS 강제 (운영) |
| `Content-Security-Policy` | `default-src 'self'; ...` | XSS/인젝션 방어 |

설정 파일: `frontend/next.config.ts`

#### CORS (FastAPI)

Backend의 CORS 설정은 `Settings.ALLOWED_ORIGINS`로 관리합니다.

| 환경 | 허용 Origin |
|------|------------|
| 개발 | `http://localhost:3000`, `http://frontend:3000` |
| 운영 | 운영 도메인만 명시 (예: `https://yourdomain.com`) |

**규칙:**
- `allow_origins: ["*"]`는 운영 환경에서 **금지**
- `allow_credentials: True` (쿠키 전송 허용)
- `allow_methods`: `GET`, `POST`, `PATCH`, `DELETE` (PUT 미사용)

설정 파일: `backend/app/main.py`, `backend/app/core/config.py`

#### CSRF 방어

이 프로젝트는 별도 CSRF 토큰 없이 다중 계층 방어를 사용합니다:

| 방어 계층 | 설명 |
|-----------|------|
| `SameSite=lax` 쿠키 | cross-site POST 요청에 쿠키 미전송 |
| BFF 프록시 | 클라이언트 → Next.js(동일 origin) → Backend |
| CORS | Backend는 허용된 origin만 접근 가능 |
| `Content-Type: application/json` | 단순 form 제출 불가 (CORS preflight 트리거) |

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

### docker-compose.yml

| 서비스 | 이미지/빌드 | 포트 | 핵심 설정 |
|--------|------------|------|-----------|
| frontend | `docker/frontend/Dockerfile` (dev) | 3000 | 소스 마운트 (`./frontend/src:/app/src`) |
| backend | `docker/backend/Dockerfile` (dev) | 8000 | uvicorn `--reload`, DB/Redis 의존 |
| db | `postgres:16-alpine` | 5432 | healthcheck, volume 영속화 |
| redis | `redis:7-alpine` | 6379 | healthcheck, volume 영속화 |

설정 파일: `docker-compose.yml`

### 환경변수

| 변수 | 서비스 | 설명 |
|------|--------|------|
| `DATABASE_URL` | backend | PostgreSQL 연결 (asyncpg) |
| `REDIS_URL` | backend | Redis 연결 |
| `SECRET_KEY` | backend | JWT 서명 키 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | backend | Access Token 만료 (기본: 15) |
| `REFRESH_TOKEN_EXPIRE_DAYS` | backend | Refresh Token 만료 (기본: 7) |
| `LOG_LEVEL` | backend | 로그 레벨 (기본: INFO) |
| `LOG_JSON` | backend | JSON 포맷 출력 (기본: true) |
| `BACKEND_URL` | frontend | Backend 내부 URL |
| `NEXT_PUBLIC_APP_NAME` | frontend | 앱 이름 (클라이언트 노출) |

설정 파일: `.env.example`

### Hot Reload

| 서비스 | 방식 | 설정 |
|--------|------|------|
| Frontend | Next.js Fast Refresh | `volumes: ./frontend/src:/app/src` |
| Backend | uvicorn `--reload` | `volumes: ./backend/app:/app/app` |

---

## 7. 배포

### Multi-stage Dockerfile

| 서비스 | Base | Development | Production |
|--------|------|-------------|------------|
| Backend | `python:3.12-slim` + requirements | uvicorn `--reload` | uvicorn `--workers 4` |
| Frontend | `node:20-alpine` + npm ci | `npm run dev` | `output: "standalone"` + `node server.js` |

설정 파일: `docker/backend/Dockerfile`, `docker/frontend/Dockerfile`

### 운영 환경 (docker-compose.prod.yml)

개발 환경과의 주요 차이:
- `target: production` (Multi-stage 빌드)
- 소스 마운트 없음 (이미지에 코드 포함)
- 환경변수를 외부에서 주입 (`${DATABASE_URL}` 등)
- 디버그 포트 미노출

설정 파일: `docker-compose.prod.yml`

### GitHub Actions CI/CD

**트리거**: `pull_request` → `main`, `develop` 브랜치

| Job | 환경 | 실행 항목 |
|-----|------|-----------|
| `frontend` | Node 20 | lint → type-check → test (coverage) |
| `backend` | Python 3.12 + PostgreSQL + Redis | ruff → mypy → pytest (coverage) |
| `e2e` | Docker Compose + Playwright | frontend/backend 통과 후 실행 |

설정 파일: `.github/workflows/ci.yml`

