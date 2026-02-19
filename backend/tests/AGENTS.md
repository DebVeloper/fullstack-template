# Backend Tests (`backend/tests/`)

pytest 기반 테스트 모음. 일부는 **실제 Postgres/Redis** 연결이 필요합니다.

## How To Run

```bash
docker compose -f infra/docker-compose.yml up -d

cd backend
uv run pytest
```

## Required Env (common)

- `DATABASE_URL_TEST` — 테스트 DB (기본: `app_test`)
- `REDIS_URL` — 테스트 Redis
- `SECRET_KEY` — JWT 서명 키 (테스트에서 monkeypatch로 override하는 케이스도 있음)

참조: `backend/.env.example`

## Fixture Patterns

- 기본 fixture는 `backend/tests/conftest.py`에서 제공
  - `db_session`: `DATABASE_URL_TEST`로 async engine 생성 후, 매 테스트마다 `create_all`/`drop_all`
  - `client`: `ASGITransport(app=app)`로 FastAPI 전체 경로를 테스트
  - `client`는 `get_db`/`get_redis`를 오버라이드하여, DB/Redis가 필요 없는 라우터 테스트를 빠르게 돌릴 수 있음

## When You Touch Auth/Redis Logic

- Refresh rotation/replay/grace period 관련 변경은 최소 아래를 함께 확인한다:
  - `backend/tests/test_refresh_rotation.py`
  - `backend/tests/test_refresh_replay_detection.py`
  - `backend/tests/test_refresh_denies_locked_user.py`

## Test Hygiene

- `app.dependency_overrides`를 사용했다면 테스트 종료 전에 반드시 `clear()`
- Redis를 직접 쓰는 테스트는 `flushdb()`로 격리 (예: refresh rotation 계열)
