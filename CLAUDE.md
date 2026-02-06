# Claude Code 프로젝트 설정

## 필수 문서

작업 시작 전 반드시 아래 문서를 숙지하세요:

1. **[ARCHITECTURE.md](./ARCHITECTURE.md)** — 기술 스택, 디렉토리 구조, 아키텍처 패턴 (BFF, JWT, 3-Layer)
2. **[CONVENTIONS.md](./CONVENTIONS.md)** — 코딩 컨벤션, Frontend/Backend 규격, API 규격, 테스팅 규격
3. **[AGENTS.md](./AGENTS.md)** — AI 에이전트 작업 규칙, 금지 사항

AGENTS.md의 모든 규칙을 엄격히 준수하세요.

## 핵심 제약

- **TDD 필수**: 테스트를 먼저 작성하고 구현한다
- **Pydantic v2**: `.model_dump()`, `ConfigDict`, `DeclarativeBase` 사용 (v1 문법 금지)
- **TypeScript strict**: `any` 금지, 모든 함수에 타입 명시
- **3-Layer 분리**: Router → Service → Repository (Router에서 직접 DB 접근 금지)
- **BFF 패턴**: 클라이언트는 Next.js API Route를 통해서만 백엔드에 접근

## 스킬 참조

추가 가이드라인이 필요하면 `.agents/skills/` 디렉토리의 스킬을 참조하세요:

- `fastapi-templates` — Backend 아키텍처 패턴
- `vercel-react-best-practices` — React/Next.js 57개 성능 규칙
- `python-patterns` — Python async/testing 패턴
- `supabase-postgres-best-practices` — PostgreSQL 최적화 30개 가이드
