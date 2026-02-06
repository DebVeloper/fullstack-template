# Agents

이 문서는 본 프로젝트에서 작업하는 AI 에이전트가 반드시 준수해야 하는 규칙을 정의합니다.

---

## 1. 일반 규칙

### 1.1 작업 전 원칙

- **파일 읽기 먼저**: 코드를 수정하기 전에 반드시 해당 파일을 읽고 이해한다
- **문서 숙지**: [ARCHITECTURE.md](./ARCHITECTURE.md)와 [CONVENTIONS.md](./CONVENTIONS.md)를 숙지하고 정의된 패턴을 따른다
- **패턴 일관성**: 기존 코드베이스의 패턴과 스타일을 따른다. 새로운 패턴을 도입하지 않는다
- **최소 변경**: 요청된 변경 사항만 수행한다. 불필요한 리팩토링이나 개선을 하지 않는다

### 1.2 설계 원칙

| 원칙 | 설명 |
|------|------|
| **YAGNI** | 현재 필요하지 않은 기능을 미리 구현하지 않는다 |
| **KISS** | 가장 단순한 해결책을 선택한다 |
| **DRY** | 반복되는 코드는 추상화하되, 2번 이상 반복될 때만 적용한다 |

### 1.3 보안 원칙

- OWASP Top 10 취약점을 항상 인지한다
- SQL Injection: ORM만 사용, raw SQL 금지
- XSS: 사용자 입력을 항상 이스케이프한다
- CSRF: 상태 변경 요청은 적절한 토큰 검증을 포함한다
- 토큰 관리: JWT는 httpOnly 쿠키에만 저장, localStorage/sessionStorage 금지
- 비밀번호: bcrypt 해싱 필수, 평문 저장/비교 금지
- 환경변수: 시크릿은 코드에 하드코딩하지 않는다

### 1.4 파일 관리

- 불필요한 파일을 생성하지 않는다
- 빈 파일을 생성하지 않는다
- 새 파일 생성 시 반드시 ARCHITECTURE.md의 디렉토리 구조에 부합하는 위치에 생성한다
- 기존 파일 수정을 우선하고, 새 파일 생성은 최소화한다

---

## 2. 코드 생성 규칙

### 2.1 TDD 필수

모든 기능 구현은 반드시 TDD 사이클을 따른다:

```
1. 실패하는 테스트 작성
2. 테스트를 통과하는 최소한의 코드 작성
3. 리팩토링 (테스트 통과 유지)
```

**테스트가 없는 코드는 미완성이다.**

### 2.2 문서 준수

- 디렉토리 구조: [ARCHITECTURE.md §3](./ARCHITECTURE.md#3-디렉토리-구조) 준수
- 코딩 컨벤션: [CONVENTIONS.md §1](./CONVENTIONS.md#1-프로젝트-컨벤션) 준수
- API 설계: [CONVENTIONS.md §4](./CONVENTIONS.md#4-api-규격) 준수
- 에러 처리: [CONVENTIONS.md §3.4](./CONVENTIONS.md#34-에러-응답-포맷) 준수

### 2.3 Import 규칙

**Frontend:**
- `@/` 절대경로 사용 (`@/components/ui/button`)
- 상대경로는 같은 디렉토리 내부에서만 허용 (`./utils`)
- Barrel file (`index.ts`에서 re-export) 사용 금지

**Backend:**
- 절대 import 우선 (`from app.models.user import User`)
- 상대 import는 같은 패키지 내에서만 허용

### 2.4 타입 안전성

**Frontend (TypeScript):**
- strict mode 필수 (`tsconfig.json`)
- `any` 타입 사용 금지
- `as` type assertion 최소화 → type guard 사용
- 모든 함수에 반환 타입 명시 (JSX 반환 제외)

**Backend (Python):**
- 모든 함수에 type hint 필수 (파라미터 + 반환값)
- `mypy --strict` 통과 필수
- `Any` 타입 사용 금지
- Pydantic v2 문법 사용 (`.model_dump()`, `ConfigDict`, `DeclarativeBase`)

---

## 3. Frontend 규칙

### 3.1 컴포넌트 패턴

- **Server Component 우선**: 기본은 Server Component. Client Component는 필요한 경우에만
- **`'use client'` 최소 범위**: 전체 페이지가 아닌, 상호작용이 필요한 최소 컴포넌트에만 적용
- **컴포넌트 분리**: 하나의 컴포넌트는 하나의 책임만 갖는다
- **Props 타입**: 모든 컴포넌트의 props는 interface로 정의한다

```typescript
// Good: 최소 범위 Client Component
// components/features/auth/login-form.tsx
"use client";

interface LoginFormProps {
  onSuccess?: () => void;
}

export function LoginForm({ onSuccess }: LoginFormProps) {
  // 상호작용 로직
}

// Good: Server Component에서 Client Component 조합
// app/(public)/login/page.tsx
import { LoginForm } from "@/components/features/auth/login-form";

export default function LoginPage() {
  return (
    <div className="flex min-h-screen items-center justify-center">
      <LoginForm />
    </div>
  );
}
```

### 3.2 TanStack Query

- [CONVENTIONS.md §2.3](./CONVENTIONS.md#23-tanstack-query-패턴) 준수

### 3.3 Tailwind CSS

- [CONVENTIONS.md §2.4](./CONVENTIONS.md#24-tailwind-css) 준수

### 3.4 접근성

- 모든 이미지에 `alt` 속성 필수 (장식용: `alt=""`)
- 인터랙티브 요소에 적절한 `aria-*` 속성
- 키보드 네비게이션 지원
- WCAG AA 기준 색상 대비 충족
- 폼 요소에 `<label>` 연결 필수

### 3.5 성능

- 이미지: `next/image` 사용 (raw `<img>` 금지)
- 링크: `next/link` 사용 (raw `<a>` 금지, 외부 링크 예외)
- 코드 분할: 무거운 컴포넌트는 `next/dynamic`으로 지연 로딩
- 번들: barrel file import 금지 → 직접 import
- 추가 규칙: `.agents/skills/vercel-react-best-practices/SKILL.md` 참조

---

## 4. Backend 규칙

### 4.1 엔드포인트 생성 순서

새로운 API 엔드포인트를 추가할 때 반드시 이 순서를 따른다:

```
1. 테스트 작성 (실패하는 테스트)
2. Pydantic 스키마 정의 (schemas/)
3. DB 모델 정의 (models/) — 필요한 경우
4. Repository 구현 (repositories/)
5. Service 구현 (services/)
6. Router 구현 (api/v1/endpoints/)
7. Router 등록 (api/v1/router.py)
8. 테스트 통과 확인
9. 리팩토링
```

### 4.2 Pydantic 필수

- [CONVENTIONS.md §3.2](./CONVENTIONS.md#32-pydantic-스키마) 준수

### 4.3 async/await

- 모든 DB 작업은 async (`AsyncSession`, `asyncpg`)
- 동기 라이브러리(예: `psycopg2`, `requests`) 사용 금지
- HTTP 클라이언트: `httpx` (async) 사용
- 파일 I/O: `aiofiles` 사용

### 4.4 DB 쿼리 최적화

- **N+1 방지**: `selectinload`/`joinedload`로 관계 즉시 로딩
- **Pagination 필수**: 전체 목록 반환 금지, 항상 `limit`/`offset` 적용
- **Index**: WHERE/JOIN 절에 사용되는 컬럼에 인덱스 추가
- **Connection Pooling**: SQLAlchemy 엔진 `pool_size`, `max_overflow` 설정
- 추가 규칙: `.agents/skills/supabase-postgres-best-practices/` 참조

### 4.5 의존성 주입

- FastAPI `Depends` 패턴 사용
- DB 세션, 인증 사용자 등은 모두 의존성으로 주입
- 테스트에서 `app.dependency_overrides`로 교체 가능하게 설계

```python
# Good
@router.get("/users/me")
async def get_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ...

# Bad — 직접 DB 접근
@router.get("/users/{id}")
async def get_user(id: int):
    async with AsyncSessionLocal() as db:  # 의존성 미사용
        ...
```

---

## 5. Git & 버전 관리

[CONVENTIONS.md §1.3](./CONVENTIONS.md#13-git-전략) 준수. 주요 규칙:

- Conventional Commits 포맷 (`type(scope): description`)
- 브랜치: `feature/`, `fix/`, `hotfix/` 접두사
- PR: CI 통과 필수, Squash merge

---

## 6. CI/CD

[ARCHITECTURE.md §7](./ARCHITECTURE.md#7-배포) 준수. 주요 규칙:

- PR 시 자동 CI (lint + type-check + test) 통과 필수
- Docker multi-stage 빌드, `.dockerignore` 활용
- 시크릿은 GitHub Secrets로 주입, 로그 출력 금지

---

## 7. 금지 사항

### 7.1 코드 금지

| 금지 항목 | 이유 | 대안 |
|-----------|------|------|
| `any` 타입 (TS) | 타입 안전성 파괴 | 명시적 타입 정의 |
| `console.log` 커밋 | 프로덕션 코드 오염 | 디버거 또는 로깅 라이브러리 |
| 하드코딩된 시크릿 | 보안 위험 | 환경변수 |
| `localStorage`에 토큰 저장 | XSS 공격 취약 | httpOnly 쿠키 |
| `dangerouslySetInnerHTML` | XSS 공격 취약 | 안전한 마크다운 렌더러 |
| Barrel file (`index.ts` re-export) | 번들 크기 증가, 순환 참조 | 직접 import |
| 동기 DB 드라이버 | 성능 저하, 블로킹 | asyncpg, aiosqlite |
| Router에서 직접 DB 접근 | 3-Layer 위반 | Service → Repository |
| `dict` 직접 반환 (BE) | 타입 안전성 없음 | Pydantic 스키마 |
| Raw SQL 쿼리 | SQL Injection 위험 | SQLAlchemy ORM |
| `.env` 파일 커밋 | 시크릿 노출 | `.env.example`만 커밋 |

### 7.2 보안 금지

| 금지 항목 | 위험 |
|-----------|------|
| 평문 비밀번호 저장/비교 | 데이터 유출 시 전체 계정 탈취 |
| JWT secret 하드코딩 | 시크릿 노출로 토큰 위조 가능 |
| CORS `allow_origins: ["*"]` (운영) | 무제한 외부 접근 허용 |
| SQL Injection 가능 코드 | 데이터베이스 전체 탈취 |
| 에러 응답에 스택트레이스 노출 | 내부 구조 정보 유출 |

### 7.3 구조 금지

| 금지 항목 | 이유 |
|-----------|------|
| ARCHITECTURE.md에 정의되지 않은 디렉토리 생성 | 프로젝트 구조 일관성 유지 |
| 승인 없이 새로운 패턴/라이브러리 도입 | 기술 부채 방지 |
| 테스트 없는 기능 제출 | TDD 필수 원칙 위반 |
| 미사용 의존성 추가 | 번들 크기/보안 표면 증가 |
