# Conventions

공통 컨벤션을 정의합니다. 영역별 상세 규격은 아래 문서를 참조하세요:

- [CONVENTIONS-FRONTEND.md](./CONVENTIONS-FRONTEND.md) — Frontend 규격 및 테스팅
- [CONVENTIONS-BACKEND.md](./CONVENTIONS-BACKEND.md) — Backend 규격 및 테스팅
- [SPECS-BACKEND.md](./SPECS-BACKEND.md) — Backend 참조 구현 코드
- [SPECS-FRONTEND.md](./SPECS-FRONTEND.md) — Frontend 참조 구현 코드

---

## 설계 원칙

모든 코드는 아래 원칙을 따릅니다:

- **YAGNI** (You Aren't Gonna Need It): 현재 필요하지 않은 기능을 미리 구현하지 않는다
- **KISS** (Keep It Simple, Stupid): 가장 단순한 해결책을 선택한다
- **DRY** (Don't Repeat Yourself): 동일한 로직의 중복을 피한다. 단, 섣부른 추상화보다는 약간의 중복이 낫다

---

## 1. 네이밍 규칙

| 대상 | 규칙 | 예시 |
|------|------|------|
| 파일 (FE) | kebab-case | `user-profile.tsx` |
| 파일 (BE) | snake_case | `user_service.py` |
| 디렉토리 | kebab-case (FE), snake_case (BE) | `features/`, `user_repository/` |
| React 컴포넌트 | PascalCase | `UserProfile` |
| React 훅 | camelCase, `use` prefix | `useUserQuery` |
| TS 함수/변수 | camelCase | `getUserById` |
| TS 타입/인터페이스 | PascalCase | `UserResponse` |
| Python 함수/변수 | snake_case | `get_user_by_id` |
| Python 클래스 | PascalCase | `UserService` |
| DB 테이블 | snake_case, 복수형 | `users`, `refresh_tokens` |
| DB 컬럼 | snake_case | `created_at`, `is_active` |
| API 경로 | kebab-case, 복수형 명사 | `/api/v1/users`, `/api/v1/auth/login` |
| 환경변수 | UPPER_SNAKE_CASE | `DATABASE_URL`, `SECRET_KEY` |
| FE 공개 환경변수 | `NEXT_PUBLIC_` prefix | `NEXT_PUBLIC_APP_NAME` |
| Git 브랜치 | kebab-case | `feature/user-auth`, `fix/login-bug` |

---

## 2. 코드 스타일

**Frontend:**
- ESLint + Prettier + TypeScript strict mode 필수
- 절대 경로 import (`@/` prefix)
- 설정 파일: [SPECS-INFRA.md §6, §8](./SPECS-INFRA.md#6-frontend-설정) 참조

**Backend:**
- Ruff (lint + format) + mypy (strict) + pytest (asyncio)
- 설정 파일: [SPECS-INFRA.md §7.1](./SPECS-INFRA.md#71-pyprojecttoml) 참조

---

## 3. Git 전략

**브랜치 구조:**

```
main ← 운영 배포 브랜치
└── develop ← 개발 통합 브랜치
    ├── feature/user-auth
    ├── feature/dashboard
    ├── fix/login-redirect
    └── hotfix/security-patch (main에서 분기)
```

**Conventional Commits:**

```
type(scope): description

# type: feat, fix, docs, style, refactor, test, chore, ci
# scope: frontend, backend, auth, users, db, docker, ci

# 예시
feat(backend): add user registration endpoint
fix(frontend): resolve login redirect loop
docs: update ARCHITECTURE.md with BFF diagram
test(backend): add auth service unit tests
chore(docker): update postgres to 16.2
```

### PR 리뷰 프로세스

**브랜치 보호 규칙 (main, develop):**
- PR을 통해서만 merge 가능 (직접 push 금지)
- 최소 1명의 리뷰어 승인 필수
- CI 통과 필수 (lint, type-check, test)
- Squash merge 사용 (커밋 히스토리 정리)

**PR 작성 규칙:**
- 제목: Conventional Commits 형식 (`feat(backend): add user registration`)
- 본문: 변경 사항 요약, 테스트 계획, 스크린샷(UI 변경 시)
- 라벨: `frontend`, `backend`, `breaking` 등

**리뷰 체크리스트:**
- [ ] 코드 컨벤션 준수 ([CONVENTIONS.md](./CONVENTIONS.md), 영역별 문서)
- [ ] 테스트 작성/통과 확인
- [ ] 보안 취약점 없음 (OWASP Top 10)
- [ ] API 변경 시 openapi-ts 재생성 확인
- [ ] 마이그레이션 파일 포함 (DB 변경 시)

### 릴리즈 프로세스

```
develop → main (PR merge) → 태그 생성 → 배포
```

1. `develop`에서 기능 개발 완료 및 QA
2. `develop` → `main` PR 생성 및 리뷰
3. merge 후 시맨틱 버전 태그 생성: `v{major}.{minor}.{patch}`
4. GitHub Actions CD 파이프라인 자동 실행
5. Hotfix: `main`에서 `hotfix/` 브랜치 분기 → `main`과 `develop` 모두에 merge

---

## 4. pre-commit Hooks

커밋 전에 자동으로 lint, format, type-check를 실행합니다.

**규칙:**
- 모든 개발자는 로컬에 pre-commit을 설치해야 합니다 (`pip install pre-commit && pre-commit install`)
- CI에서는 개별 도구를 직접 실행하여 동일한 검증 수행
- hook 실패 시 커밋 불가

설정 파일: [SPECS-INFRA.md §5.1](./SPECS-INFRA.md#51-pre-commit-configyaml) 참조

---

## 5. API 규격

### 5.1 RESTful 설계

| 메서드 | 용도 | 예시 |
|--------|------|------|
| `GET` | 리소스 조회 | `GET /api/v1/users` |
| `POST` | 리소스 생성 | `POST /api/v1/users` |
| `PATCH` | 리소스 부분 수정 | `PATCH /api/v1/users/{id}` |
| `DELETE` | 리소스 삭제 | `DELETE /api/v1/users/{id}` |

**규칙:**
- 복수형 명사 사용 (`/users`, `/posts`)
- `PUT` 미사용 → `PATCH`만 사용 (부분 업데이트)
- 중첩 리소스는 최대 2단계 (`/users/{id}/posts`)

### 5.2 버전 관리

- URL 기반 버전: `/api/v1/`
- 라우터 등록: `app.include_router(api_router, prefix="/api/v1")`

### 5.3 응답 포맷

**단일 리소스:**

```json
{
  "id": "550e8400-...",
  "email": "user@example.com",
  "name": "홍길동",
  "is_active": true,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

**페이지네이션 리스트:**

```json
{
  "items": [...],
  "total": 42,
  "page": 1,
  "size": 20,
  "pages": 3
}
```

**에러:** [ARCHITECTURE.md §4.3](./ARCHITECTURE.md#43-에러-핸들링) 참조 ([구현 코드 → SPECS-BACKEND.md §1.5](./SPECS-BACKEND.md#15-error-schemas--exception-hierarchy))

### 5.4 페이지네이션 / 필터링

**페이지네이션 (offset-based):**

| 파라미터 | 타입 | 기본값 | 설명 |
|----------|------|--------|------|
| `page` | int | 1 | 현재 페이지 (1-based) |
| `size` | int | 20 | 페이지당 항목 수 (max: 100) |

**정렬:**

| 파라미터 | 타입 | 기본값 | 설명 |
|----------|------|--------|------|
| `sort_by` | string | `created_at` | 정렬 기준 필드 |
| `order` | string | `desc` | `asc` 또는 `desc` |

**필터링:**
- Query parameter 기반: `GET /api/v1/users?is_active=true&name=홍`
- 검색: `GET /api/v1/users?q=홍길동` (전체 텍스트 검색)

### 5.5 OpenAPI 스펙 품질

FastAPI 엔드포인트에 아래 메타데이터를 반드시 명시합니다:

- `response_model`: 모든 엔드포인트에 명시 (openapi-ts 타입 생성에 필수)
- `tags`: 리소스 단위로 그룹화 (`["users"]`, `["auth"]`)
- `responses`: 주요 에러 응답 코드와 모델을 명시 (4xx, 5xx)
- `summary`: 엔드포인트 설명 (한글 허용)

### 5.6 JSON 필드 네이밍

**Backend JSON 응답은 snake_case를 사용합니다.**

Pydantic v2는 기본적으로 Python 필드명(snake_case)을 그대로 JSON 키로 사용합니다. camelCase 자동 변환(`alias_generator`)은 사용하지 않습니다.

```json
// ✅ 올바른 예시 (snake_case)
{ "is_active": true, "created_at": "2024-01-01T00:00:00Z" }

// ❌ 잘못된 예시 (camelCase)
{ "isActive": true, "createdAt": "2024-01-01T00:00:00Z" }
```

**Frontend에서의 처리:**
- openapi-ts가 생성하는 타입과 SDK는 Backend의 snake_case를 그대로 반영
- Frontend 코드에서도 API 데이터 접근 시 snake_case 사용: `user.is_active`, `user.created_at`
- camelCase ↔ snake_case 자동 변환 라이브러리 사용 금지 (타입 불일치 유발)

**범위:**
- API 요청/응답 body: snake_case
- Query parameter: snake_case (`?sort_by=created_at&is_active=true`)
- URL path: kebab-case (`/api/v1/auth/login`) — [§1 네이밍 규칙](#1-네이밍-규칙) 참조

---

## 6. 테스팅 원칙

### 6.1 TDD 워크플로우

모든 기능 개발은 반드시 **Red → Green → Refactor** 사이클을 따릅니다.

```
1. Red    — 실패하는 테스트 먼저 작성
2. Green  — 테스트를 통과하는 최소한의 코드 작성
3. Refactor — 코드 정리 (테스트는 계속 통과해야 합니다)
```

**테스트 없는 기능은 미완성입니다.**

### 6.2 커버리지 기준

| 영역 | 최소 커버리지 |
|------|-------------|
| Backend Services | 90% |
| Backend Repositories | 80% |
| Backend API Endpoints | 85% |
| Frontend Hooks (queries) | 80% |
| Frontend Components (features) | 75% |
| Frontend Components (ui) | 측정 제외 (shadcn) |
| Frontend E2E (Playwright) | 주요 사용자 흐름 100% |

영역별 테스트 설정은 [CONVENTIONS-BACKEND.md §8](./CONVENTIONS-BACKEND.md#8-테스팅-pytest)과 [CONVENTIONS-FRONTEND.md §7](./CONVENTIONS-FRONTEND.md#7-테스팅)을 참조하세요.

### 6.3 통합 테스트 전략

**FE↔BE 통합 검증은 Playwright E2E 테스트가 담당합니다.**

```
E2E 테스트 환경:
  Docker Compose (frontend + backend + db + redis)
  ↓
  Playwright → Browser → Next.js(BFF) → FastAPI → PostgreSQL/Redis
```

| 테스트 유형 | 도구 | 대상 | 환경 |
|------------|------|------|------|
| Frontend 단위 | vitest + RTL + MSW | 컴포넌트, 훅 | jsdom (모킹) |
| Backend 단위 | pytest + httpx | Repository, Service | 테스트 DB |
| Backend API 통합 | pytest + AsyncClient | 엔드포인트 전체 경로 | 테스트 DB + Redis |
| FE↔BE 통합 (E2E) | Playwright | 전체 사용자 흐름 | Docker Compose |

**Backend API 통합 테스트:**
- `httpx.AsyncClient` + `ASGITransport`로 FastAPI 앱 전체를 테스트
- DB, Redis 실제 연결 (테스트 DB 사용)
- 매 테스트마다 `create_all` / `drop_all`로 격리

**E2E 통합 테스트:**
- CI에서 `docker compose up` 후 Playwright 실행
- 주요 사용자 시나리오: 회원가입 → 로그인 → 인증된 페이지 접근 → 로그아웃
- 인증 흐름, 에러 처리, 페이지 네비게이션 검증

---

## 7. 환경 & 설정

환경변수 네이밍은 [§1 네이밍 규칙](#1-네이밍-규칙)을 참조하세요. Docker 개발/운영 환경은 [ARCHITECTURE.md §6, §7](./ARCHITECTURE.md#6-개발-환경)을 참조하세요.

### 시크릿 관리

| 환경 | 방식 |
|------|------|
| 로컬 개발 | `.env` 파일 (`.gitignore`에 등록) |
| CI/CD | GitHub Secrets |
| 운영 | 환경변수 주입 (Docker / 클라우드 시크릿) |

**`.env` 파일은 절대 커밋하지 않습니다.** `.env.example`만 커밋합니다.
