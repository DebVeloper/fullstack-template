# Claude Code 프로젝트 설정

## 필수 문서

작업 시작 전 반드시 아래 문서를 숙지한다:

- [ARCHITECTURE.md](./ARCHITECTURE.md) — 아키텍처 및 기술 스택
- [AUTH.md](./AUTH.md) — 인증/인가 설계
- [CONVENTIONS.md](./CONVENTIONS.md) — 공통 컨벤션
- [CONVENTIONS-FRONTEND.md](./CONVENTIONS-FRONTEND.md) — Frontend 컨벤션
- [CONVENTIONS-BACKEND.md](./CONVENTIONS-BACKEND.md) — Backend 컨벤션
- [SPECS-BACKEND.md](./SPECS-BACKEND.md) / [SPECS-FRONTEND.md](./SPECS-FRONTEND.md) / [SPECS-INFRA.md](./SPECS-INFRA.md) — 참조 구현 코드

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
- **보안 준수**: 아래 §3 금지 사항을 반드시 확인한다

### 1.2 파일 관리

- 불필요한 파일을 생성하지 않는다
- 빈 파일을 생성하지 않는다
- 새 파일 생성 시 반드시 ARCHITECTURE.md의 디렉토리 구조에 부합하는 위치에 생성한다
- 기존 파일 수정을 우선하고, 새 파일 생성은 최소화한다

---

## 2. 코드 생성 규칙

### 2.1 TDD 필수

모든 기능은 [CONVENTIONS.md §6.1 TDD 워크플로우](./CONVENTIONS.md#61-tdd-워크플로우)를 따른다.

### 2.2 문서 우선순위

**문서 우선순위**: 프로젝트 문서 > 스킬 예시 코드. 충돌 시 프로젝트 문서가 우선한다

---

## 3. 금지 사항

**AI 에이전트 추가 금지:**

| 금지 항목 | 이유 |
|-----------|------|
| ARCHITECTURE.md에 정의되지 않은 디렉토리 생성 | 프로젝트 구조 일관성 유지 |
| 승인 없이 새로운 패턴/라이브러리 도입 | 기술 부채 방지 |
| 테스트 없는 기능 제출 | TDD 필수 원칙 위반 |
| 미사용 의존성 추가 | 번들 크기/보안 표면 증가 |

---

## 스킬 참조

추가 가이드라인이 필요하면 아래 스킬을 참조한다:

**Backend** (`.agents/skills/`):
- `fastapi-templates` — FastAPI 프로젝트 구조, async 패턴, 의존성 주입, 에러 처리
- `python-patterns` — Python 개발 원칙, async 패턴, 타입 힌트, 프로젝트 구조
- `supabase-postgres-best-practices` — PostgreSQL 쿼리 최적화, 인덱스, 커넥션 관리 (30개 규칙)

**Frontend** (`.agents/skills/`):
- `next-best-practices` — Next.js 파일 컨벤션, RSC 경계, 데이터 패턴, 메타데이터, 번들 최적화
- `vercel-react-best-practices` — React/Next.js 성능 최적화 (Vercel 엔지니어링 가이드, 57개 규칙)
- `frontend-design` — UI 컴포넌트/페이지 제작 시 디자인 품질 가이드
- `web-design-guidelines` — UI 코드 리뷰, 접근성 감사, UX 베스트 프랙티스

**Frontend — UI/UX** (plugin):
- `/ui-ux-pro-max` — UI/UX 디자인 (50개 스타일, 21개 팔레트, 50개 폰트 페어링, shadcn/ui 통합)
