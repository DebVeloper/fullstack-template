# Conventions

공통 컨벤션을 정의합니다. 영역별 상세 규격은 아래 문서를 참조하세요:

- [CONVENTIONS-FRONTEND.md](./CONVENTIONS-FRONTEND.md) — Frontend 규격 및 테스팅
- [CONVENTIONS-BACKEND.md](./CONVENTIONS-BACKEND.md) — Backend 규격 및 테스팅
- [SPECS-BACKEND.md](./SPECS-BACKEND.md) — Backend 참조 구현 코드
- [SPECS-FRONTEND.md](./SPECS-FRONTEND.md) — Frontend 참조 구현 코드

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
- ESLint: `next/core-web-vitals`, `next/typescript`
- Prettier: `semi: true`, `singleQuote: false`, `tabWidth: 2`, `trailingComma: "all"`, `printWidth: 80`
- TypeScript strict mode 필수
- 절대 경로 import (`@/` prefix)

**Backend:**
- Ruff: `line-length = 88`, `target-version = "py312"`, `select = ["E", "F", "W", "I", "N", "UP", "B", "A", "SIM"]`
- mypy: `strict = true`, Pydantic plugin 활성화
- pytest: `asyncio_mode = "auto"`

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

---

## 4. pre-commit Hooks

커밋 전에 자동으로 lint, format, type-check를 실행합니다. 설정: `.pre-commit-config.yaml`

| Hook | 대상 | 도구 |
|------|------|------|
| Frontend Lint | `*.ts`, `*.tsx` | `next lint` |
| Frontend Type Check | `*.ts`, `*.tsx` | `tsc --noEmit` |
| Frontend Format | `*.ts`, `*.tsx` | `prettier --check` |
| Backend Lint + Fix | `backend/` | `ruff --fix` |
| Backend Format | `backend/` | `ruff-format` |
| Backend Type Check | `backend/` | `mypy --strict` |

**규칙:**
- 모든 개발자는 로컬에 pre-commit을 설치해야 합니다 (`pip install pre-commit && pre-commit install`)
- CI에서는 개별 도구를 직접 실행하여 동일한 검증 수행
- hook 실패 시 커밋 불가

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
