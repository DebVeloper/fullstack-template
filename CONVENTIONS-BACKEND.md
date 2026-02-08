# Backend Conventions

> 공통 컨벤션(네이밍, Git, API 규격 등)은 [CONVENTIONS.md](./CONVENTIONS.md)를 참조하세요.
> 참조 구현 코드(보일러플레이트)는 [SPECS-BACKEND.md](./SPECS-BACKEND.md)를 참조하세요.

---

## 1. 3-Layer 구조

Router(HTTP) → Service(비즈니스) → Repository(데이터) 계층을 엄격히 분리합니다.

**BaseRepository 패턴** — 구현 코드는 [SPECS-BACKEND.md §1.1](./SPECS-BACKEND.md#11-baserepository)을 참조하세요.
- 도메인 Repository는 BaseRepository를 상속하고 커스텀 쿼리 메서드 추가
- `flush()` 사용 (commit이 아닌) — 세션 컨텍스트가 commit 관리
- 모듈 레벨 싱글턴 인스턴스 생성: `user_repository = UserRepository(User)`

**config.py** — 구현 코드는 [SPECS-BACKEND.md §1.2](./SPECS-BACKEND.md#12-settings)를 참조하세요. `BaseSettings` 상속, `ConfigDict(env_file=".env")` 패턴.

**database.py** — 구현 코드는 [SPECS-BACKEND.md §1.3](./SPECS-BACKEND.md#13-database-session)을 참조하세요. `get_db`: commit on success, rollback on error.

**Service 계층 규칙:**
- 비즈니스 로직을 처리하고 여러 Repository를 조합
- 트랜잭션은 `get_db()` 세션 컨텍스트가 관리 (Service에서 commit/rollback 호출 금지)
- Redis 접근(캐시/세션)은 Service에서 직접 수행, 복잡해지면 별도 Repository로 분리

**async/await 필수:**
- 모든 DB 작업은 async (`AsyncSession`, `asyncpg`)
- 동기 라이브러리(예: `psycopg2`, `requests`) 사용 금지
- HTTP 클라이언트: `httpx` (async) 사용
- 파일 I/O: `aiofiles` 사용

**의존성 주입:**

```python
# 의존성 주입 예시
@router.get("/users/me")
async def get_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ...
```

- FastAPI `Depends` 패턴 사용
- DB 세션, 인증 사용자 등은 모두 의존성으로 주입
- 테스트에서 `app.dependency_overrides`로 교체 가능하게 설계
- 직접 세션 생성 금지 (`AsyncSessionLocal()` 등) — 반드시 `Depends(get_db)` 사용

---

## 2. 엔드포인트 생성 순서

새로운 API 엔드포인트를 추가할 때 반드시 이 순서를 따릅니다:

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

---

## 3. Pydantic 스키마

Create / Update / Response 스키마를 분리합니다.

구현 코드는 [SPECS-BACKEND.md §3](./SPECS-BACKEND.md#3-pydantic-schemas)를 참조하세요.

**규칙:**
- `model_config = ConfigDict(from_attributes=True)` 사용 (Response 스키마)
- `.model_dump()` 사용 (`.dict()` 금지)
- `.model_validate()` 사용 (`.from_orm()` 금지)
- `Optional[X]` 대신 `X | None` 사용 (Python 3.12+)

---

## 4. JWT 인증 상세

인증 흐름 및 토큰 구조는 [ARCHITECTURE.md §4.2](./ARCHITECTURE.md#42-jwt-인증-흐름)를 참조하세요.
Security 함수 시그니처와 인증 의존성 코드는 [SPECS-BACKEND.md §2](./SPECS-BACKEND.md#2-auth)를 참조하세요.

**인증 규칙:**
- 토큰 구성 및 흐름은 [ARCHITECTURE.md §4.2](./ARCHITECTURE.md#42-jwt-인증-흐름) 참조
- `OAuth2PasswordBearer` + `Depends`로 인증 주입
- 인증 실패 시 401 `UNAUTHORIZED` 반환

---

## 5. 에러 응답 포맷

에러 JSON 포맷과 커스텀 예외 계층은 [ARCHITECTURE.md §4.3](./ARCHITECTURE.md#43-에러-핸들링)을 참조하세요.
에러 스키마 구현 코드는 [SPECS-BACKEND.md §1.5](./SPECS-BACKEND.md#15-error-schemas--exception-hierarchy)를 참조하세요.

**규칙:**
- 모든 커스텀 예외는 `AppException`을 상속
- `RequestValidationError` → 422 `VALIDATION_ERROR`로 변환
- `main.py`에 `@app.exception_handler(AppException)`, `@app.exception_handler(RequestValidationError)` 등록
- Frontend에서 `error.code` 값으로 분기하여 사용자 메시지 표시

---

## 6. DB 모델 / 마이그레이션

Base 모델과 TimestampMixin 구현 코드는 [SPECS-BACKEND.md §1.4](./SPECS-BACKEND.md#14-base-model--timestampmixin)를 참조하세요.
마이그레이션 워크플로우는 [ARCHITECTURE.md §4.4](./ARCHITECTURE.md#44-db-마이그레이션)를 참조하세요.

**규칙:**
- 모든 테이블은 UUID v4를 Primary Key로 사용 (`uuid.uuid4` default)
- 모든 `datetime`은 UTC로 저장/전송, `DateTime(timezone=True)` 필수
- FK 컬럼에 `index=True` 필수 (JOIN 성능)
- Alembic 마이그레이션은 `--autogenerate`로 생성, 의미 있는 메시지 작성
- 운영 DB에 `downgrade` 금지

---

## 7. DB 쿼리 최적화

- **N+1 방지**: `selectinload`/`joinedload`로 관계 즉시 로딩
- **Pagination 필수**: 전체 목록 반환 금지, 항상 `limit`/`offset` 적용
- **Index**: WHERE/JOIN 절에 사용되는 컬럼에 인덱스 추가
- **FK Index 필수**: 모든 Foreign Key 컬럼에 `index=True` 설정 (JOIN 성능 최적화)
- **Connection Pooling**: SQLAlchemy 엔진 `pool_size`, `max_overflow` 설정
- 추가 규칙: `.agents/skills/supabase-postgres-best-practices/` 참조

---

## 8. 테스팅 (pytest)

**디렉토리 구조:**

```
tests/
├── conftest.py              # 공유 fixture (engine, db_session, client)
├── test_auth.py             # 인증 테스트
├── test_users.py            # 사용자 테스트
├── services/                # 서비스 단위 테스트
└── repositories/            # 레포지토리 단위 테스트
```

**핵심 fixture 패턴** — 구현 코드는 [SPECS-BACKEND.md §1.6](./SPECS-BACKEND.md#16-conftestpy-fixture)을 참조하세요.
- `engine` (session scope): 테스트 DB 엔진
- `db_session` (function scope): 매 테스트마다 `create_all` → yield session → `drop_all`
- `client` (function scope): `AsyncClient` + `app.dependency_overrides[get_db]` 오버라이드

**커버리지 기준:** [CONVENTIONS.md §6.2](./CONVENTIONS.md#62-커버리지-기준) 참조.

**네이밍 규칙:**
- 파일: `test_{module}.py`
- 함수: `test_{action}_{condition}_{expected}` (예: `test_create_user_with_valid_data_returns_201`)
- fixture: 명사형 (`db_session`, `authenticated_client`)
