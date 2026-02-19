# Claude Code 프로젝트 설정

## 필수 문서

작업 시작 전 반드시 아래 문서를 숙지한다:

- [ARCHITECTURE.md](./ARCHITECTURE.md) — 아키텍처 및 기술 스택
- [AUTH.md](./AUTH.md) — 인증/인가 설계
- [CONVENTIONS.md](./CONVENTIONS.md) — 공통 컨벤션
- [CONVENTIONS-FRONTEND.md](./CONVENTIONS-FRONTEND.md) — Frontend 컨벤션
- [CONVENTIONS-BACKEND.md](./CONVENTIONS-BACKEND.md) — Backend 컨벤션
- [SPECS-BACKEND.md](./SPECS-BACKEND.md) / [SPECS-FRONTEND.md](./SPECS-FRONTEND.md) / [SPECS-INFRA.md](./SPECS-INFRA.md) — 참조 구현 코드

## 핵심 제약

- **TDD 필수**: 테스트를 먼저 작성하고 구현한다
- **Pydantic v2**: `.model_dump()`, `ConfigDict`, `DeclarativeBase` 사용 (v1 문법 금지)
- **TypeScript strict**: `any` 금지, 모든 함수에 타입 명시
- **3-Layer 분리**: Router → Service → Repository (Router에서 직접 DB 접근 금지)
- **BFF 패턴**: 클라이언트는 Next.js API Route를 통해서만 백엔드에 접근

## 빠른 네비게이션

### AGENTS 계층 (작업 위치별 추가 규칙)

- `backend/AGENTS.md` — FastAPI/DB/Redis/3-Layer 규칙 + 명령어
- `backend/tests/AGENTS.md` — pytest fixture/통합 테스트(DB/Redis) 실행 규칙
- `backend/app/services/AGENTS.md` — refresh rotation/replay detection, Google OAuth exchange, 세션 무효화
- `frontend/AGENTS.md` — Next.js 15(App Router)/BFF/auth 쿠키 규칙 + 명령어
- `frontend/src/app/api/AGENTS.md` — BFF proxy(`[...path]`) + auth route handlers 규칙
- `frontend/src/client/AGENTS.md` — openapi-ts 자동 생성 코드(수동 수정 금지)
- `frontend/src/hooks/queries/AGENTS.md` — TanStack Query 커스텀 훅/키 팩토리 패턴
- `frontend/src/components/AGENTS.md` — 컴포넌트 구조(layouts/features), a11y/perf 규칙
- `frontend/e2e/AGENTS.md` — Playwright E2E + test-login(AUTH_TEST_MODE) 실행 규칙
- `infra/AGENTS.md` — docker compose(Postgres/Redis) + initdb 규칙

### 핵심 엔트리포인트 (코드 네비게이션 시작점)

- Backend: `backend/app/main.py`, `backend/app/api/v1/router.py`, `backend/app/api/dependencies.py`
- Backend(Auth): `backend/app/api/v1/endpoints/auth.py`, `backend/app/services/auth_service.py`
- Frontend(BFF): `frontend/src/app/api/[...path]/route.ts`
- Frontend(Auth): `frontend/src/app/api/auth/*/route.ts`, `frontend/src/lib/auth-cookies.ts`, `frontend/src/middleware.ts`
- Frontend(Dashboard): `frontend/src/app/(auth)/layout.tsx`, `frontend/src/components/layouts/dashboard-shell.tsx`

### 자주 쓰는 명령어 (로컬)

- Infra: `docker compose -f infra/docker-compose.yml up -d`
- Backend: `cd backend && uv sync && uv run alembic upgrade head && uv run ruff check . && uv run mypy --strict . && uv run pytest`
- Frontend: `cd frontend && pnpm install && pnpm lint && pnpm typecheck && pnpm test && pnpm run build`
- E2E: `cd frontend && AUTH_TEST_MODE=true AUTH_TEST_SECRET=change-me pnpm test:e2e`
- Generate API client: `cd frontend && pnpm run generate:api` (backend `:8000` 실행 필요)

### 단일 테스트 실행 (자주 씀)

- Backend(pytest)
  - 파일: `cd backend && uv run pytest tests/test_users_me.py`
  - 단일 테스트: `cd backend && uv run pytest tests/test_users_me.py::test_get_users_me_returns_current_user_with_is_admin_true`
  - 패턴: `cd backend && uv run pytest -k "refresh"`
- Frontend(vitest)
  - 파일: `cd frontend && pnpm test -- src/tests/bff-proxy.test.ts`
  - 단일 테스트명: `cd frontend && pnpm test -- -t "should refresh on 401"`
- E2E(Playwright)
  - spec: `cd frontend && AUTH_TEST_MODE=true AUTH_TEST_SECRET=change-me pnpm test:e2e -- e2e/auth-admin.spec.ts`
  - grep: `cd frontend && AUTH_TEST_MODE=true AUTH_TEST_SECRET=change-me pnpm test:e2e -- -g "superadmin"`

### 전역 하드 룰 (요약)

- `.env`는 절대 커밋하지 않는다 (`.env.example`만 커밋)
- Browser는 Backend(FastAPI)에 직접 호출 금지 → Next.js `/api/*` (BFF)만 사용
- 토큰 저장소는 httpOnly 쿠키만 허용 (`localStorage` 금지)
- Backend auth는 `Set-Cookie` 금지 → JSON body로 토큰 반환, 쿠키 설정은 BFF가 담당
- API 요청/응답 JSON 키는 `snake_case` 고정 (camelCase 변환 라이브러리 금지)
- 업데이트는 `PUT` 금지 → `PATCH`만 사용
- FastAPI 엔드포인트는 `response_model` 필수 (openapi-ts 타입 생성 의존)
- `frontend/src/client/`는 자동 생성 코드 → 수동 수정 금지, 필요 시 `pnpm run generate:api`

### 코드 스타일 (요약)

- **Imports**
  - TS/TSX: 내부 모듈은 `@/*` alias 선호 (`frontend/tsconfig.json`), barrel import 금지
  - Python: `from app...` absolute import 사용, 표준→서드파티→로컬 순서 (ruff `I` 규칙)
- **Formatting**
  - Python: ruff 기준 line-length 88 (`backend/pyproject.toml`)
  - TS/TSX: 프로젝트에 prettier 없음 → 파일/디렉토리 기존 스타일을 따른다 (불필요한 reformat 금지)
- **Types**
  - TS strict + `any` 금지; `unknown`을 좁혀서 사용
  - Python mypy strict; `cast()`는 최후 수단, 가능한 타입을 모델링(TypedDict 등)
- **Naming / API**
  - JSON key는 `snake_case` 고정; camelCase 변환 라이브러리 금지
  - 업데이트는 `PUT` 금지 → `PATCH`만 사용
- **Error Handling**
  - Backend: `AppException` 기반 unified error envelope 사용, stacktrace/민감정보 노출 금지
  - Frontend: `{ error: { code, message, details } }` envelope를 기본으로 처리 (`frontend/src/lib/api-error.ts`)

### Cursor/Copilot 규칙

- Cursor rules: 없음 (`.cursor/`, `.cursorrules` 미존재)
- Copilot instructions: 없음 (`.github/copilot-instructions.md` 미존재)

---

## 1. 일반 규칙

### 1.1 작업 전 원칙

- **파일 읽기 먼저**: 코드를 수정하기 전에 반드시 해당 파일을 읽고 이해한다
- **문서 숙지**: 위 필수 문서를 숙지하고 정의된 패턴을 따른다
- **패턴 일관성**: 기존 코드베이스의 패턴과 스타일을 따른다. 새로운 패턴을 도입하지 않는다
- **최소 변경**: 요청된 변경 사항만 수행한다. 불필요한 리팩토링이나 개선을 하지 않는다
- **보안 준수**: 아래 §3 금지 사항을 반드시 확인한다

### 1.2 파일 관리

- 불필요한 파일을 생성하지 않는다
- 빈 파일을 생성하지 않는다
- 새 파일 생성 시 반드시 ARCHITECTURE.md의 디렉토리 구조에 부합하는 위치에 생성한다
- 기존 파일 수정을 우선하고, 새 파일 생성은 최소화한다

---

## 2. 코드 생성 규칙

### 2.1 TDD 필수

모든 기능은 [CONVENTIONS.md §6.1 TDD 워크플로우](./CONVENTIONS.md#61-tdd-워크플로우)를 따른다.

### 2.2 문서 우선순위

**문서 우선순위**: 프로젝트 문서 > 스킬 예시 코드. 충돌 시 프로젝트 문서가 우선한다

---

## 3. 금지 사항

**AI 에이전트 추가 금지:**

| 금지 항목 | 이유 |
|-----------|------|
| ARCHITECTURE.md에 정의되지 않은 디렉토리 생성 | 프로젝트 구조 일관성 유지 |
| 승인 없이 새로운 패턴/라이브러리 도입 | 기술 부채 방지 |
| 테스트 없는 기능 제출 | TDD 필수 원칙 위반 |
| 미사용 의존성 추가 | 번들 크기/보안 표면 증가 |

---

## 스킬 참조

추가 가이드라인이 필요하면 아래를 참조한다:

- Backend: `.agents/skills/fastapi-templates/`, `.agents/skills/python-patterns/`, `.agents/skills/supabase-postgres-best-practices/`
- Frontend: `.agents/skills/next-best-practices/`, `.agents/skills/vercel-react-best-practices/`, `.agents/skills/frontend-design/`, `.agents/skills/web-design-guidelines/`
- UI/UX plugin: `/ui-ux-pro-max`
