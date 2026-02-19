# Backend (`backend/`)

FastAPI backend (Python 3.12+, async SQLAlchemy, Redis async).

## Where To Look

- App entrypoint + error envelope: `backend/app/main.py`
- Router composition: `backend/app/api/v1/router.py`
- HTTP endpoints: `backend/app/api/v1/endpoints/`
- Auth/admin dependencies: `backend/app/api/dependencies.py`
- Business logic: `backend/app/services/`
- DB access: `backend/app/repositories/`
- Settings/env contract: `backend/app/core/config.py`
- Migrations: `backend/alembic/`, `backend/alembic.ini`
- Tests: `backend/tests/` (see `backend/tests/AGENTS.md`)

## Commands

- Start infra: `docker compose -f infra/docker-compose.yml up -d`
- Setup env: `cp backend/.env.example backend/.env`
- Install deps: `cd backend && uv sync`
- Apply migrations: `cd backend && uv run alembic upgrade head`
- Run server: `cd backend && uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000`
- Run tests: `cd backend && uv run pytest`
- Lint: `cd backend && uv run ruff check .`
- Typecheck: `cd backend && uv run mypy --strict .`

## Hard Rules (Backend)

- Async-only: sync libs (`requests`, `psycopg2`) 사용 금지
- 3-Layer 엄수: Router → Service → Repository (Router에서 직접 DB 접근 금지)
- Transaction: Service에서 commit/rollback 호출 금지 (`get_db()` 컨텍스트가 관리)
- Pydantic v2: `.model_dump()`/`.model_validate()` 사용 (`.dict()`/`.from_orm()` 금지)
- Error response: `AppException` + `ErrorResponse` envelope 사용; stacktrace 노출 금지

## Env Gotchas

- Settings는 `env_file=".env"`를 사용한다 (`backend/`에서 실행하거나 env var를 export해야 함)
- `AUTH_TEST_MODE=true`면 `AUTH_TEST_SECRET`가 반드시 필요하다 (`backend/app/core/config.py`에서 검증)
- `DATABASE_URL_TEST`는 실제 테스트 DB를 가리켜야 한다 (infra initdb가 기본 `app_test` 생성)
