# Frontend (`frontend/`)

Next.js 15 (App Router) + BFF 패턴. 브라우저는 **Next.js `/api/*`만 호출**하고 FastAPI로 직접 접근하지 않습니다.

## Where To Look

- App Router root: `frontend/src/app/layout.tsx`
- Public login page: `frontend/src/app/(public)/login/page.tsx`
- Auth-protected layout + dashboard shell: `frontend/src/app/(auth)/layout.tsx`, `frontend/src/components/layouts/dashboard-shell.tsx`
- Route protection: `frontend/src/middleware.ts`

### BFF (API Routes)

- Catch-all proxy: `frontend/src/app/api/[...path]/route.ts`
- Auth routes (cookie ownership): `frontend/src/app/api/auth/*/route.ts`
- Cookie helpers: `frontend/src/lib/auth-cookies.ts`

### API Client

- Generated OpenAPI client: `frontend/src/client/` (see `frontend/src/client/AGENTS.md`)
- Generated client runtime config + error mapping: `frontend/src/lib/api-client.ts`, `frontend/src/lib/api-error.ts`

## Commands

```bash
cd frontend
pnpm install
pnpm lint
pnpm typecheck
pnpm test
pnpm test:e2e
pnpm run generate:api
```

## Hard Rules (Frontend)

- Backend 직접 호출 금지: 브라우저/컴포넌트는 `/api/v1/*`를 **항상** Next.js로 호출
- 토큰 저장은 httpOnly 쿠키만 허용 (`localStorage` 금지)
- Next.js 15 비동기 API: `cookies()`, `headers()`, `searchParams` 등은 `await` 필수
- `frontend/src/client/`는 자동 생성 코드 → 수동 수정 금지

## Testing Notes

- Unit: `vitest` (config: `frontend/vitest.config.ts`)
- E2E: `playwright` (config: `frontend/playwright.config.ts`, tests: `frontend/e2e/`)
- E2E의 test-login은 `AUTH_TEST_MODE=true` + `AUTH_TEST_SECRET`가 필요 (see `frontend/e2e/AGENTS.md`)
