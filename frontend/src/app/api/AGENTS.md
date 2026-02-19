# Frontend BFF API Routes (`frontend/src/app/api/`)

Next.js Route Handler로 구성된 BFF 계층.

## Core Entry Points

- Catch-all proxy: `frontend/src/app/api/[...path]/route.ts`
- Auth routes:
  - `frontend/src/app/api/auth/google/login/route.ts`
  - `frontend/src/app/api/auth/google/callback/route.ts`
  - `frontend/src/app/api/auth/refresh/route.ts`
  - `frontend/src/app/api/auth/logout/route.ts`
  - `frontend/src/app/api/auth/test-login/route.ts`

## Proxy Rules (Catch-all)

- Request URL 변환 규칙은 `createBackendUrl()`에 정의되어 있다
- `Authorization: Bearer <access_token>` 헤더는 `access_token` httpOnly 쿠키에서 만든다
- Hop-by-hop 헤더(`connection`, `transfer-encoding` 등)는 제거해서 프록시한다
- Backend가 401이면 1회에 한해 refresh를 시도하고 원 요청을 재시도한다
  - refresh 성공 시 쿠키 교체 (`setAuthCookies`)
  - refresh 실패 또는 재시도 후에도 401이면 쿠키 삭제 (`clearAuthCookies`) + 401 반환
- refresh dedupe는 모듈 레벨 `refreshPromise`로 처리한다 (같은 인스턴스 내 중복 호출 방지)

## Auth Routes (Cookie Ownership)

- Backend는 쿠키를 설정하지 않는다 → BFF가 `frontend/src/lib/auth-cookies.ts`로 httpOnly 쿠키를 설정
- `refresh_token` 쿠키 path는 `/api` (silent refresh는 `/api/v1/*` 프록시에서 수행)

## E2E-only Test Login

- `AUTH_TEST_MODE!="true"`면 `/api/auth/test-login`은 404를 반환한다
- `AUTH_TEST_SECRET`는 반드시 필요하며, backend 호출 시 `x-test-auth-secret` 헤더로 전달한다
