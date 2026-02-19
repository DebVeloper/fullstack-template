# E2E (`frontend/e2e/`)

Playwright E2E 테스트. 외부 Google OAuth를 쓰지 않고 **test-login**으로 인증을 우회합니다.

## How To Run

```bash
docker compose -f infra/docker-compose.yml up -d

cd backend
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

cd ../frontend
pnpm install

AUTH_TEST_MODE=true \
AUTH_TEST_SECRET=change-me \
ADMIN_EMAIL=admin@example.com \
pnpm test:e2e
```

## Key Files

- Test suite: `frontend/e2e/auth-admin.spec.ts`, `frontend/e2e/smoke.spec.ts`
- Config: `frontend/playwright.config.ts`

## Env Gotchas

- `AUTH_TEST_MODE=true` + non-empty `AUTH_TEST_SECRET`가 없으면 auth/admin E2E는 skip된다
- Playwright는 `PLAYWRIGHT_BASE_URL`이 없으면 `pnpm dev`로 Next dev server를 띄운다
- `AUTH_TEST_MODE=true`일 때 기본 `reuseExistingServer=false`라서 3000 포트 점유에 민감하다
