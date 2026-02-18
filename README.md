# Fullstack Template

풀스택 웹 서비스를 빠르게 시작하기 위한 **재사용 가능한 프로젝트 템플릿**입니다.

**기술 스택:** Next.js 15 (App Router) + FastAPI + PostgreSQL + Redis

이 템플릿은 **Google OAuth(OIDC) 로그인만**을 기본으로 합니다 (email/password 회원가입/로그인 기본 제공 없음).

---

## Quick Start

### 1) Infra (PostgreSQL + Redis)

```bash
docker compose -f infra/docker-compose.yml up -d
```

### 2) Backend (FastAPI, 로컬 실행)

```bash
cp backend/.env.example backend/.env
# backend/.env에서 SECRET_KEY, ADMIN_EMAIL, GOOGLE_OAUTH_* 값을 설정하세요.

cd backend
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 3) Frontend (Next.js, 로컬 실행)

```bash
cd frontend
pnpm install
cp .env.example .env.local
pnpm dev
```

접속 확인:
- Frontend: http://localhost:3000/login
- Backend API 문서: http://localhost:8000/docs
- PostgreSQL: localhost:5432
- Redis: localhost:6379

## 주요 명령어

| 명령어 | 설명 |
|--------|------|
| `docker compose -f infra/docker-compose.yml up -d` | DB/Redis 시작 |
| `docker compose -f infra/docker-compose.yml down -v` | DB/Redis 중지 (볼륨 삭제) |
| `cd backend && uv run alembic upgrade head` | DB 마이그레이션 적용 |
| `cd backend && uv run pytest` | Backend 테스트 실행 |
| `cd frontend && pnpm test` | Frontend 테스트 실행 (vitest, coverage 포함) |
| `cd frontend && AUTH_TEST_MODE=true AUTH_TEST_SECRET=change-me pnpm test:e2e` | E2E 테스트 실행 (test-login 필요) |
| `cd frontend && pnpm run generate:api` | openapi-ts 타입 재생성 (backend 실행 필요) |

## 문서 가이드

| 문서 | 설명 |
|------|------|
| [ARCHITECTURE.md](./ARCHITECTURE.md) | 기술 스택, 디렉토리 구조, 아키텍처 패턴 (BFF, JWT, 3-Layer) |
| [AUTH.md](./AUTH.md) | 인증/인가 통합 가이드 (JWT, Token Rotation, BFF 쿠키, 참조 구현) |
| [CONVENTIONS.md](./CONVENTIONS.md) | 공통 컨벤션 (네이밍, Git, API 규격, 테스팅 원칙) |
| [CONVENTIONS-FRONTEND.md](./CONVENTIONS-FRONTEND.md) | Frontend 컨벤션 (App Router, TanStack Query, Tailwind, 접근성, 성능) |
| [CONVENTIONS-BACKEND.md](./CONVENTIONS-BACKEND.md) | Backend 컨벤션 (3-Layer, Pydantic, DB, 로깅) |
| [SPECS-BACKEND.md](./SPECS-BACKEND.md) | Backend 참조 구현 코드 |
| [SPECS-FRONTEND.md](./SPECS-FRONTEND.md) | Frontend 참조 구현 코드 |
| [SPECS-INFRA.md](./SPECS-INFRA.md) | Infrastructure 참조 구현 코드 (Docker, CI/CD, 설정 파일) |
| [AGENTS.md](./AGENTS.md) | AI 에이전트 규칙 및 프로젝트 설정 |
