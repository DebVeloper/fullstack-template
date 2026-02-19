# Components (`frontend/src/components/`)

UI 컴포넌트 레이어.

## Structure

- Layout components: `frontend/src/components/layouts/`
  - Dashboard shell: `frontend/src/components/layouts/dashboard-shell.tsx`
  - LNB: `frontend/src/components/layouts/lnb.tsx`
  - Query provider: `frontend/src/components/layouts/query-provider.tsx`
- Feature components: `frontend/src/components/features/`
  - Admin users: `frontend/src/components/features/admin/`

## Hard Rules

- 최소 범위의 `'use client'`만 사용한다 (layout/feature 중 브라우저 기능이 필요한 곳만)
- 접근성 우선: `aria-*`, label, focus-visible, skip link, 터치 타겟 규칙 준수
- 성능 규칙 준수: raw `<img>`/raw `<a>` 사용 금지(외부 링크 예외), barrel import 금지

## Navigation/Auth Coupling

- LNB의 admin-only 노출은 `/api/v1/users/me`의 `is_admin`에 의존한다 (`useCurrentUser`)
