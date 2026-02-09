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
1. 로그인
   Client ──POST /api/auth/login──▶ BFF ──▶ FastAPI
                                              │
                                              ├─ 사용자 인증 (bcrypt 비교)
                                              ├─ Access Token 생성 (JWT, 15분)
                                              ├─ Refresh Token 생성 (UUID)
                                              ├─ Redis에 Refresh Token 저장
                                              │
   Client ◀── Set-Cookie(httpOnly) ◀── BFF ◀──┘

2. 인증된 요청
   Client ──GET /api/users/me──▶ BFF ──▶ FastAPI
                                          │
                                          ├─ Authorization 헤더에서 JWT 추출
                                          ├─ JWT 검증 (서명, 만료)
                                          ├─ 사용자 조회
                                          │
   Client ◀── 200 User ◀── BFF ◀─────────┘

3. 토큰 갱신
   Client ──POST /api/auth/refresh──▶ BFF ──▶ FastAPI
                                       │        │
                                       │        ├─ Body에서 refresh_token 추출
                                       │        ├─ Redis에서 유효성 확인
                                       │        ├─ 기존 Refresh Token 삭제 (Rotation)
                                       │        ├─ 새 Access + Refresh Token 생성
                                       │        ├─ Redis에 새 Refresh Token 저장
                                       │        │
   Client ◀── Set-Cookie(httpOnly) ◀── BFF ◀──┘
                                       │
                                       └─ 쿠키에서 refresh_token 추출 → Body로 Backend에 전달

4. 로그아웃
   Client ──POST /api/auth/logout──▶ BFF ──▶ FastAPI
                                              │
                                              ├─ Redis에서 Refresh Token 삭제
                                              │
   Client ◀── Clear-Cookie ◀── BFF ◀─────────┘

5. 회원가입 (자동 로그인)
   Client ──POST /api/auth/register──▶ BFF ──▶ FastAPI
                                                  │
                                                  ├─ UserCreate 스키마 검증
                                                  ├─ 이메일 중복 확인
                                                  ├─ 비밀번호 해싱 + 사용자 생성
                                                  │
                                              BFF ◀──┘ (UserResponse)
                                                  │
                                                  ├─ BFF가 동일 credentials로 login API 호출
                                                  ├─ 토큰 수신 → 쿠키 설정
                                                  │
   Client ◀── Set-Cookie(httpOnly) ◀── BFF ◀──┘
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
| `refresh_token` | UUID v4 | true | true (prod) | lax | `/api/auth` | 7일 (604800초) |

> **refresh_token path 제한 (`/api/auth`):** 브라우저는 `path=/api/auth` 쿠키를 `/api/auth/*` 요청에만 자동 전송합니다.
> BFF 프록시의 Silent Refresh는 Next.js 서버 사이드에서 실행되므로, `cookies()` API를 통해
> path와 무관하게 모든 쿠키에 접근할 수 있습니다. 이 설계는 보안(불필요한 쿠키 전송 방지)과
> 기능(Silent Refresh)을 모두 충족합니다.

- **Backend 응답**: `TokenResponse { access_token, refresh_token, token_type }` (JSON body)
- **BFF 역할**: Backend 응답 수신 → `Set-Cookie` 헤더로 httpOnly 쿠키 설정 → 클라이언트에 전달
- **Logout**: BFF가 쿠키 삭제 (`maxAge=0`) + Backend에 refresh_token body 전송 → Redis 삭제

**CSRF 방어:** 이 프로젝트는 별도 CSRF 토큰 없이 다중 계층 방어(SameSite=lax 쿠키, BFF 프록시, CORS, Content-Type)를 사용합니다. 상세는 [ARCHITECTURE.md §4.5](./ARCHITECTURE.md#45-보안)를 참조하세요.

---

## 6. 참조 구현

Auth 관련 Backend 구현 코드(스키마, Security 함수, AuthService, 인증 의존성, 엔드포인트)는 [SPECS-BACKEND.md §3](./SPECS-BACKEND.md#3-auth)을 참조하세요.

Auth 관련 Frontend 구현 코드(쿠키 헬퍼, BFF 인증 라우트, 인증 미들웨어, 로그인 폼, Auth Hooks)는 [SPECS-FRONTEND.md §1.2~1.12](./SPECS-FRONTEND.md)를 참조하세요.

---

## 7. 인증 규칙 체크리스트

**Backend:**
- [ ] 비밀번호는 bcrypt로 해싱 (평문 저장/비교 금지)
- [ ] JWT secret은 환경변수(`SECRET_KEY`)로 관리 (하드코딩 금지)
- [ ] Refresh Token은 Redis에 저장, TTL 설정
- [ ] Token Rotation + Replay Detection 적용
- [ ] Rate Limiting: login 5/min, refresh 10/min
- [ ] 인증 실패 시 401 `UNAUTHORIZED` 반환
- [ ] 에러 응답에 스택트레이스 노출 금지

**Frontend:**
- [ ] 토큰은 httpOnly 쿠키에만 저장 (`localStorage` 금지)
- [ ] BFF가 쿠키 설정 (Backend는 JSON body만 반환)
- [ ] Auth 요청은 BFF 전용 라우트 사용 (openapi-ts SDK 미사용)
- [ ] Silent Refresh: BFF 프록시에서 자동 토큰 갱신
- [ ] 401 도달 시 `/login` 리다이렉트 (QueryClient 글로벌 핸들러)
- [ ] `refresh_token` 쿠키 path는 `/api/auth`로 제한
- [ ] BFF 프록시 테스트: 인증 헤더 전달, Silent Refresh, 에러 전달 ([SPECS-FRONTEND.md §1.9](./SPECS-FRONTEND.md#19-bff-프록시-테스트))
