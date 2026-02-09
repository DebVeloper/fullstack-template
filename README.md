# Fullstack Template

풀스택 웹 서비스를 빠르게 시작하기 위한 **재사용 가능한 프로젝트 템플릿**입니다.

**기술 스택:** Next.js 15 (App Router) + FastAPI + PostgreSQL + Redis

---

## Quick Start

```bash
# 1. 프로젝트 클론
git clone https://github.com/debveloper/fullstack-template.git my-project
cd my-project

# 2. 환경변수 설정
cp .env.example .env
# .env 파일을 열어 SECRET_KEY 등 필수 값 설정

# 3. 개발 환경 실행
docker compose up -d

# 4. DB 마이그레이션
docker compose exec backend alembic upgrade head

# 5. 접속 확인
# Frontend: http://localhost:3000
# Backend API 문서: http://localhost:8000/docs
# PostgreSQL: localhost:5432
# Redis: localhost:6379
```

## 주요 명령어

| 명령어 | 설명 |
|--------|------|
| `docker compose up -d` | 전체 서비스 시작 |
| `docker compose down` | 전체 서비스 중지 |
| `docker compose logs -f backend` | Backend 로그 확인 |
| `docker compose exec backend alembic revision --autogenerate -m "msg"` | DB 마이그레이션 생성 |
| `docker compose exec backend pytest` | Backend 테스트 실행 |
| `docker compose exec frontend npm test` | Frontend 테스트 실행 |
| `docker compose exec frontend npx playwright test` | E2E 테스트 실행 |
| `docker compose exec frontend npm run generate:api` | openapi-ts 타입 재생성 |

## 문서 가이드

| 문서 | 설명 |
|------|------|
| [ARCHITECTURE.md](./ARCHITECTURE.md) | 기술 스택, 디렉토리 구조, 아키텍처 패턴 (BFF, JWT, 3-Layer) |
| [AUTH.md](./AUTH.md) | 인증/인가 통합 가이드 (JWT, Token Rotation, BFF 쿠키, 참조 구현) |
| [CONVENTIONS.md](./CONVENTIONS.md) | 공통 컨벤션 (네이밍, Git, API 규격, 테스팅 원칙) |
| [CONVENTIONS-FRONTEND.md](./CONVENTIONS-FRONTEND.md) | Frontend 컨벤션 (App Router, TanStack Query, Tailwind, 접근성, 성능) |
| [CONVENTIONS-BACKEND.md](./CONVENTIONS-BACKEND.md) | Backend 컨벤션 (3-Layer, Pydantic, DB, 로깅) |
| [SPECS-BACKEND.md](./SPECS-BACKEND.md) | Backend 참조 구현 코드 |
| [SPECS-FRONTEND.md](./SPECS-FRONTEND.md) | Frontend 참조 구현 코드 |
| [SPECS-INFRA.md](./SPECS-INFRA.md) | Infrastructure 참조 구현 코드 (Docker, CI/CD, 설정 파일) |
| [CLAUDE.md](./CLAUDE.md) | Claude Code 프로젝트 설정 및 AI 에이전트 규칙 |
