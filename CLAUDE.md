# Claude Code 프로젝트 설정

## 필수 문서

작업 시작 전 반드시 아래 문서를 숙지한다:

1. **[ARCHITECTURE.md](./ARCHITECTURE.md)** — 기술 스택, 디렉토리 구조, 아키텍처 패턴 (BFF, JWT, 3-Layer)
2. **[CONVENTIONS.md](./CONVENTIONS.md)** — 공통 컨벤션 (네이밍, Git, API 규격, 테스팅 원칙)
3. **[CONVENTIONS-FRONTEND.md](./CONVENTIONS-FRONTEND.md)** — Frontend 규격 (App Router, TanStack Query, Tailwind, 접근성, 성능)
4. **[CONVENTIONS-BACKEND.md](./CONVENTIONS-BACKEND.md)** — Backend 규격 (3-Layer, Pydantic, JWT, DB)
5. **[SPECS-BACKEND.md](./SPECS-BACKEND.md)** / **[SPECS-FRONTEND.md](./SPECS-FRONTEND.md)** — 참조 구현 코드

## 핵심 제약

- **TDD 필수**: 테스트를 먼저 작성하고 구현한다
- **Pydantic v2**: `.model_dump()`, `ConfigDict`, `DeclarativeBase` 사용 (v1 문법 금지)
- **TypeScript strict**: `any` 금지, 모든 함수에 타입 명시
- **3-Layer 분리**: Router → Service → Repository (Router에서 직접 DB 접근 금지)
- **BFF 패턴**: 클라이언트는 Next.js API Route를 통해서만 백엔드에 접근

---

## 1. 일반 규칙

### 1.1 작업 전 원칙

- **파일 읽기 먼저**: 코드를 수정하기 전에 반드시 해당 파일을 읽고 이해한다
- **문서 숙지**: 위 필수 문서를 숙지하고 정의된 패턴을 따른다
- **패턴 일관성**: 기존 코드베이스의 패턴과 스타일을 따른다. 새로운 패턴을 도입하지 않는다
- **최소 변경**: 요청된 변경 사항만 수행한다. 불필요한 리팩토링이나 개선을 하지 않는다
- **설계 원칙**: YAGNI, KISS, DRY 원칙을 따른다 ([CONVENTIONS.md](./CONVENTIONS.md))
- **보안 준수**: 아래 §3.1, §3.2 금지 사항을 반드시 확인한다

### 1.2 파일 관리

- 불필요한 파일을 생성하지 않는다
- 빈 파일을 생성하지 않는다
- 새 파일 생성 시 반드시 ARCHITECTURE.md의 디렉토리 구조에 부합하는 위치에 생성한다
- 기존 파일 수정을 우선하고, 새 파일 생성은 최소화한다

---

## 2. 코드 생성 규칙

### 2.1 TDD 필수

모든 기능은 반드시 **Red → Green → Refactor** 사이클을 따른다. 상세 워크플로우는 [CONVENTIONS.md §6.1](./CONVENTIONS.md#61-tdd-워크플로우)을 참조한다.

- 새로운 사용자 흐름 추가 시 Playwright E2E 테스트도 함께 작성한다
- E2E 테스트는 주요 시나리오만 커버한다 (세부 로직은 단위 테스트)

### 2.2 문서 준수

- 디렉토리 구조: [ARCHITECTURE.md §3](./ARCHITECTURE.md#3-디렉토리-구조) 준수
- 코딩 컨벤션: [CONVENTIONS.md §1](./CONVENTIONS.md#1-네이밍-규칙) 준수
- API 설계: [CONVENTIONS.md §5](./CONVENTIONS.md#5-api-규격) 준수
- 에러 처리: [ARCHITECTURE.md §4.3](./ARCHITECTURE.md#43-에러-핸들링) 준수
- **문서 우선순위**: 프로젝트 문서 > 스킬 예시 코드. 충돌 시 프로젝트 문서가 우선한다

### 2.3 코드 스타일 준수

Import 규칙, 타입 안전성 등 코드 스타일은 아래 문서를 따른다:
- 공통: [CONVENTIONS.md §2](./CONVENTIONS.md#2-코드-스타일)
- Frontend: [CONVENTIONS-FRONTEND.md](./CONVENTIONS-FRONTEND.md)
- Backend: [CONVENTIONS-BACKEND.md](./CONVENTIONS-BACKEND.md)

---

## 3. 금지 사항

### 3.1 코드 금지

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
| `src/client/` 수동 수정 | 자동 생성 파일 오염 | `npx @hey-api/openapi-ts`로 재생성 |
| 수동 API 타입 정의 | openapi-ts와 중복/불일치 위험 | 생성된 타입 import |
| Integer PK | 예측 가능한 ID | UUID v4 사용 |

### 3.2 보안 금지

| 금지 항목 | 위험 |
|-----------|------|
| 평문 비밀번호 저장/비교 | 데이터 유출 시 전체 계정 탈취 |
| JWT secret 하드코딩 | 시크릿 노출로 토큰 위조 가능 |
| CORS `allow_origins: ["*"]` (운영) | 무제한 외부 접근 허용 |
| SQL Injection 가능 코드 | 데이터베이스 전체 탈취 |
| 에러 응답에 스택트레이스 노출 | 내부 구조 정보 유출 |

### 3.3 구조 금지

| 금지 항목 | 이유 |
|-----------|------|
| ARCHITECTURE.md에 정의되지 않은 디렉토리 생성 | 프로젝트 구조 일관성 유지 |
| 승인 없이 새로운 패턴/라이브러리 도입 | 기술 부채 방지 |
| 테스트 없는 기능 제출 | TDD 필수 원칙 위반 |
| 미사용 의존성 추가 | 번들 크기/보안 표면 증가 |

---

## 스킬 참조

추가 가이드라인이 필요하면 `.agents/skills/` 디렉토리의 스킬을 참조한다:

- `fastapi-templates` — Backend 아키텍처 패턴
- `vercel-react-best-practices` — React/Next.js 57개 성능 규칙
- `python-patterns` — Python async/testing 패턴
- `supabase-postgres-best-practices` — PostgreSQL 최적화 30개 가이드
