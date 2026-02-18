# Authentication & Authorization

> 인증/인가의 설계 전략, 규칙, 참조 구현을 통합한 문서입니다.

**관련 문서:**

| 문서 | 관련 내용 |
|------|----------|
| [ARCHITECTURE.md](./ARCHITECTURE.md) | BFF 패턴, 데이터 흐름, 보안 |
| [CONVENTIONS-BACKEND.md](./CONVENTIONS-BACKEND.md) | 3-Layer 구조, 의존성 주입 |
| [CONVENTIONS-FRONTEND.md](./CONVENTIONS-FRONTEND.md) | App Router, TanStack Query |
| [SPECS-BACKEND.md](./SPECS-BACKEND.md) | Redis 의존성 (§2.3) |
| [SPECS-FRONTEND.md](./SPECS-FRONTEND.md) | BFF 프록시 (§1.1), BFF 프록시 테스트 (§1.9) |

---

## 1. 개요

JWT 기반 인증과 BFF(Backend For Frontend) 패턴을 사용합니다.

- **로그인 방식**: Google OAuth(OIDC) only (Authorization Code + PKCE)
- **Access Token**: JWT (HS256, 15분) — httpOnly 쿠키
- **Refresh Token**: UUID v4 (7일) — Redis + httpOnly 쿠키
- **쿠키 설정**: BFF (Next.js API Route)가 담당 — Backend는 JSON body로 토큰 반환
- **Token Rotation**: Refresh 시 기존 토큰 폐기, 새 토큰 발급
- **Replay Detection**: Token Family 패턴으로 토큰 탈취 조기 감지

---

## 2. 토큰 구성

| 토큰 | 형식 | 만료 | 저장소 |
|------|------|------|--------|
| Access Token | JWT (HS256) | 15분 | httpOnly 쿠키 |
| Refresh Token | UUID v4 | 7일 | Redis + httpOnly 쿠키 |

---

## 3. 인증 플로우

```
1. Google OAuth 로그인 시작
   Client ──GET /api/auth/google/login──▶ Next.js (BFF)
                                           │
                                           └─ Google authorize로 redirect (state + PKCE)

2. Google OAuth 콜백
   Client ──GET /api/auth/google/callback──▶ Next.js (BFF)
                                               │
                                               ├─ state/code_verifier 검증
                                               ├─ POST /api/v1/auth/google/exchange (Backend)
                                               └─ 토큰 수신 → httpOnly 쿠키 설정 → /dashboard redirect

3. 인증된 API 요청
   Client ──GET /api/v1/users/me──▶ Next.js (BFF catch-all) ──▶ FastAPI
                                       │
                                       └─ 쿠키 access_token → Authorization 헤더 첨부

4. Silent Refresh (자동 토큰 갱신)
   Backend 401 응답 시 Next.js (BFF)가 refresh_token 쿠키로
   POST /api/v1/auth/refresh를 호출하여 Rotation을 수행하고 원 요청을 1회 재시도합니다.

5. 로그아웃
   Client ──POST /api/auth/logout──▶ Next.js (BFF) ──▶ FastAPI (/api/v1/auth/logout)
                                       │
                                       └─ 쿠키 삭제 + Redis 세션 정리

6. (E2E 전용) Test Login
   Client(Playwright) ──POST /api/auth/test-login──▶ Next.js (BFF)
                                                      │
                                                      └─ POST /api/v1/auth/test-login (Backend)
```

---

## 4. Refresh Token Rotation & Replay Detection

### 4.1 Token Family 전략

각 로그인 세션마다 고유 `family_id`를 할당합니다 (UUID v4). Redis에 family별 현재 유효 토큰을 추적하고, Rotation 시 family는 유지하면서 토큰만 교체합니다.

### 4.2 Redis Key 구조

| Key 패턴 | Value | TTL | 용도 |
|----------|-------|-----|------|
| `refresh_token:{token}` | `{user_id}:{family_id}` | 7일 | 토큰 → 사용자/패밀리 매핑 |
| `token_family:{family_id}` | 현재 유효한 token | 7일 | 패밀리별 최신 토큰 추적 |
| `user_families:{user_id}` | SET of family_id | 무제한 | 사용자의 모든 세션 추적 |

### 4.3 Replay 감지 시나리오

| 상황 | 판단 | Backend 동작 |
|------|------|-------------|
| 토큰이 Redis에 없음 | 이미 rotation됨 또는 만료 | 로그 기록, 401 반환 |
| 토큰은 있지만 family의 현재 토큰과 불일치 | **탈취 확정** — 정상 사용자는 새 토큰을 받았는데 구 토큰이 재사용됨 | 해당 사용자의 **모든 세션 무효화** (user_families의 모든 family 삭제) → 401 + "Token reuse detected. All sessions revoked." |
| 토큰과 family 토큰이 일치 | 정상 요청 | Rotation 수행 (기존 삭제 → 신규 발급) |

### 4.4 Grace Period

서버리스 환경(Vercel 등)에서 여러 인스턴스가 동시에 같은 refresh_token으로 요청할 수 있습니다. Rotation된 구 토큰에 **10초 유예기간**을 적용하여 이를 정상 처리합니다. BFF의 Promise 캐싱은 같은 인스턴스 내에서만 동작하므로, Grace Period가 인스턴스 간 동시 요청을 보완합니다.

**다중 탭 시나리오:** 사용자가 탭 A, B를 동시에 열어둔 경우, 두 탭에서 거의 동시에 refresh 요청이 발생할 수 있습니다.
- **같은 Next.js 인스턴스:** BFF 프록시의 모듈 레벨 `refreshPromise` 캐싱이 동작하여 하나의 refresh만 실행됩니다. 두 번째 요청은 동일 Promise를 반환받아 같은 결과를 사용합니다.
- **다른 인스턴스(서버리스):** 각 인스턴스가 독립적으로 refresh를 실행합니다. 첫 번째 요청이 Rotation을 수행하면 구 토큰에 Grace Period(10초)가 설정되므로, 두 번째 요청도 Grace Period 내에는 정상 처리됩니다. Grace Period 이후에 구 토큰이 재사용되면 Replay Detection이 작동합니다.

### 4.5 필수 테스트 시나리오

| # | 시나리오 | 입력 조건 | 기대 결과 |
|---|---------|----------|----------|
| 1 | 정상 Refresh | 유효한 refresh_token | 새 access_token + refresh_token 발급, 구 토큰 Grace Period 후 삭제 |
| 2 | 만료 토큰 | Redis에 없는 refresh_token | 401 반환, "Invalid or expired refresh token" |
| 3 | Replay 감지 | 이미 Rotation된 토큰 (family 불일치) | 해당 사용자 **모든 세션 무효화**, 401 반환 |
| 4 | Grace Period 내 동시 요청 | 같은 refresh_token으로 10초 이내 2회 요청 | 두 요청 모두 성공 (Grace Period 허용) |
| 5 | 로그아웃 후 사용 | 로그아웃으로 삭제된 refresh_token | 401 반환, "Invalid or expired refresh token" |

---

## 5. 쿠키 전략

Backend는 JSON body로 토큰을 반환하고, BFF(Next.js API Route)가 쿠키를 설정합니다. Backend auth 엔드포인트는 `Set-Cookie` 헤더를 사용하지 않습니다.

| 쿠키 | 값 | httpOnly | secure | sameSite | path | maxAge |
|------|-----|----------|--------|----------|------|--------|
| `access_token` | JWT 문자열 | true | true (prod) | lax | `/` | 15분 (900초) |
| `refresh_token` | UUID v4 | true | true (prod) | lax | `/api` | 7일 (604800초) |

> **refresh_token path (`/api`):** Silent Refresh는 `/api/v1/*` 요청을 처리하는 BFF catch-all에서 실행됩니다.
> 브라우저는 쿠키 `path`가 매칭되는 요청에만 쿠키를 전송하므로, refresh_token은 `/api/v1/*`에도 포함되어야 합니다.
> 따라서 refresh_token은 `/api`로 scope 하여 `/api/v1/*` 및 `/api/auth/*`에서 모두 사용 가능하게 합니다.

- **Backend 응답**: `TokenResponse { access_token, refresh_token, token_type }` (JSON body)
- **BFF 역할**: Backend 응답 수신 → `Set-Cookie` 헤더로 httpOnly 쿠키 설정 → 클라이언트에 전달
- **Logout**: BFF가 쿠키 삭제 (`maxAge=0`) + Backend에 refresh_token body 전송 → Redis 삭제

**CSRF 방어:** 이 프로젝트는 별도 CSRF 토큰 없이 다중 계층 방어(SameSite=lax 쿠키, BFF 프록시, CORS, Content-Type)를 사용합니다. 상세는 [ARCHITECTURE.md §4.5](./ARCHITECTURE.md#45-보안)를 참조하세요.

---

## 6. 참조 구현

Auth 관련 Backend 구현 코드(스키마, AuthService, Google OAuth exchange, refresh/logout, test-login gate)는 [SPECS-BACKEND.md](./SPECS-BACKEND.md)를 참조하세요.

Auth 관련 Frontend 구현 코드(BFF 프록시, 쿠키 헬퍼, Google OAuth 라우트, refresh/logout, test-login gate, 미들웨어)는 [SPECS-FRONTEND.md](./SPECS-FRONTEND.md)를 참조하세요.

---

## 7. 인증 규칙 체크리스트

**Backend:**
- [ ] JWT secret은 환경변수(`SECRET_KEY`)로 관리 (하드코딩 금지)
- [ ] Refresh Token은 Redis에 저장, TTL 설정
- [ ] Token Rotation + Replay Detection 적용
- [ ] Google OAuth: state + PKCE 필수, open redirect 금지
- [ ] Test-login은 E2E 전용: `AUTH_TEST_MODE=true` + secret header gate, 비활성 시 404, OpenAPI 노출 금지
- [ ] 인증 실패 시 401 `UNAUTHORIZED` 반환
- [ ] 에러 응답에 스택트레이스 노출 금지

**Frontend:**
- [ ] 토큰은 httpOnly 쿠키에만 저장 (`localStorage` 금지)
- [ ] BFF가 쿠키 설정 (Backend는 JSON body만 반환)
- [ ] Auth 요청은 Next.js `/api/*`로만 수행 (브라우저에서 Backend 직접 호출 금지)
- [ ] Silent Refresh: BFF 프록시에서 자동 토큰 갱신
- [ ] 401 도달 시 `/login` 리다이렉트 (QueryClient 글로벌 핸들러)
- [ ] `refresh_token` 쿠키 path는 `/api`
- [ ] Test-login은 E2E 전용: 비활성 시 `/api/auth/test-login`은 404
- [ ] BFF 프록시 테스트: 인증 헤더 전달, Silent Refresh, 에러 전달 ([SPECS-FRONTEND.md](./SPECS-FRONTEND.md))
