# Services (`backend/app/services/`)

Service 계층(비즈니스 로직). Auth/Google OAuth/관리자 기능의 핵심 로직이 집중되어 있습니다.

## Main Modules

- Token issuing/rotation/replay detection: `backend/app/services/auth_service.py`
- Admin user management (lock/unlock/soft-delete + superadmin 보호): `backend/app/services/admin_user_service.py`
- Google OAuth exchange + id_token verify(JWKS/RS256): `backend/app/services/google_oauth_service.py`

## Auth Rotation Invariants

- refresh rotation은 Lua(EVAL)로 **원자적**으로 수행한다 (`auth_service._REFRESH_ROTATION_LUA`)
- Grace period(10s) 내 구 토큰 재사용은 허용하되, 이후 재사용은 replay로 판단하여 세션 전체 무효화
- Redis key contract는 `AUTH.md`의 표/시나리오와 일치해야 한다

## Test/Login Gate (E2E only)

- Backend endpoint: `backend/app/api/v1/endpoints/auth.py`의 `/test-login`
  - `include_in_schema=False`
  - `AUTH_TEST_MODE=true`일 때만 활성
  - `x-test-auth-secret`를 `compare_digest`로 검증

## Change Checklist

- 문서/테스트 동기화:
  - `AUTH.md`
  - `backend/tests/test_refresh_rotation.py`
  - `frontend/src/tests/bff-proxy-refresh.test.ts` (BFF silent refresh 동작)
