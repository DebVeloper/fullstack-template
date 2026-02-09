# Backend Conventions

> 공통 컨벤션(네이밍, Git, API 규격 등)은 [CONVENTIONS.md](./CONVENTIONS.md)를 참조하세요.
> 참조 구현 코드는 [SPECS-BACKEND.md](./SPECS-BACKEND.md)를 참조하세요.

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
- Redis 접근 원칙 상세는 [ARCHITECTURE.md §5.2](./ARCHITECTURE.md#52-3-layer-아키텍처)를 참조

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

**3-Layer 예외 규칙:**
- 인증 의존성(`get_current_user`)은 횡단 관심사이므로, Service 계층을 경유하지 않고 **Repository를 직접 호출**하여 사용자를 조회합니다 ([SPECS-BACKEND.md §3.4](./SPECS-BACKEND.md#34-인증-의존성) 참조)
- 단, 비즈니스 로직(활성 상태 확인 외의 복잡한 로직)은 포함하지 않습니다

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

구현 코드는 [SPECS-BACKEND.md §4](./SPECS-BACKEND.md#4-pydantic-schemas)를 참조하세요.

**규칙:**
- `model_config = ConfigDict(from_attributes=True)` 사용 (Response 스키마)
- `.model_dump()` 사용 (`.dict()` 금지)
- `.model_validate()` 사용 (`.from_orm()` 금지)
- `Optional[X]` 대신 `X | None` 사용 (Python 3.12+)

---

## 4. JWT 인증

이 프로젝트는 JWT(HS256) + Refresh Token Rotation 기반 인증을 사용합니다. JWT 라이브러리는 PyJWT(`import jwt`)를 사용합니다. 인증/인가의 전체 설계(토큰 구성, Token Rotation, Replay Detection, 쿠키 전략), 규칙, 참조 구현은 [AUTH.md](./AUTH.md)를 참조하세요.

---

## 5. 에러 응답 포맷

통합 에러 JSON 포맷(`ErrorResponse`)을 사용합니다. 에러 계층 구조는 [ARCHITECTURE.md §4.3](./ARCHITECTURE.md#43-에러-핸들링), 구현 코드는 [SPECS-BACKEND.md §1.5](./SPECS-BACKEND.md#15-error-schemas--exception-hierarchy)를 참조하세요.

**규칙:**
- 모든 커스텀 예외는 `AppException`을 상속
- `RequestValidationError` → 422 `VALIDATION_ERROR`로 변환
- `main.py`에 exception handler 등록 필수
- Frontend에서 `error.code` 값으로 분기하여 사용자 메시지 표시

---

## 6. DB 모델 / 마이그레이션

구현 코드(Base, TimestampMixin)는 [SPECS-BACKEND.md §1.4](./SPECS-BACKEND.md#14-base-model--timestampmixin)를 참조하세요.

**규칙:**
- PK 전략은 [ARCHITECTURE.md §4.4](./ARCHITECTURE.md#44-db-마이그레이션) 참조 (UUID v4)
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

**FakeRedis + Lua 테스트:** `fakeredis[lua]` 패키지를 사용하면 Lua 스크립트(Token Rotation 등)를 실제 Redis 없이 인메모리로 테스트할 수 있습니다. `conftest.py`의 `FakeRedis(decode_responses=True)` 인스턴스가 Lua 스크립트를 지원합니다.

**네이밍 규칙:**
- 파일: `test_{module}.py`
- 함수: `test_{action}_{condition}_{expected}` (예: `test_create_user_with_valid_data_returns_201`)
- fixture: 명사형 (`db_session`, `authenticated_client`)

---

## 9. Rate Limiting

인증 엔드포인트에 IP 기반 rate limiting을 적용합니다.

**라이브러리:** `slowapi` (FastAPI 전용)

**적용 대상 및 제한:**

| 엔드포인트 | 제한 | 근거 |
|-----------|------|------|
| `POST /api/v1/auth/login` | 5/minute | brute-force 방어 |
| `POST /api/v1/auth/refresh` | 10/minute | silent refresh 동시 요청 고려 |

**규칙:**
- `slowapi.Limiter`를 커스텀 `_get_client_ip` key_func으로 초기화 (프록시 환경의 `X-Forwarded-For` 처리)
- 인증 엔드포인트에만 `@limiter.limit()` 데코레이터 적용
- 429 응답도 프로젝트 통합 에러 포맷(`ErrorResponse`)을 따름
- 운영 환경에서는 Redis 스토리지 백엔드 사용 (다중 인스턴스 대응)
- 구현 코드는 [SPECS-BACKEND.md §1.7](./SPECS-BACKEND.md#17-rate-limiting) 참조

---

## 10. 로깅 전략

**라이브러리:** `structlog` (구조화된 JSON 로깅)

**로그 레벨:**

| 레벨 | 용도 | 예시 |
|------|------|------|
| `DEBUG` | 개발 디버깅 | SQL 쿼리, 내부 상태 변화 |
| `INFO` | 주요 이벤트 추적 | 로그인 성공, API 호출, 작업 완료 |
| `WARNING` | 비정상이지만 복구 가능 | Replay 토큰 감지, Rate limit 도달 |
| `ERROR` | 오류 발생 (복구 가능) | 외부 API 실패, DB 일시 오류 |
| `CRITICAL` | 시스템 장애 | DB 연결 불가, 메모리 부족 |

**구조화된 로깅 (structlog):**

운영 환경에서는 JSON 포맷으로 로깅하여 로그 수집 시스템(ELK, CloudWatch)과 연동합니다.

초기 설정 코드는 [SPECS-BACKEND.md §1.8](./SPECS-BACKEND.md#18-로깅-설정)을 참조하세요.

```python
import structlog

logger = structlog.get_logger()

# 사용 예시
logger.info("login_success", user_id=str(user.id))
logger.warning("token_replay_detected", user_id=user_id_str, family_id=family_id)
```

로그 포맷 예시와 주요 로깅 지점은 [SPECS-BACKEND.md §5](./SPECS-BACKEND.md#5-로깅-참조)를 참조하세요.

**로깅 규칙:**

1. **컨텍스트 정보 포함**: `user_id`, `request_id`, `ip` 등 추적 가능한 식별자
2. **민감 정보 제외**: 비밀번호, 토큰 전체 값(최대 앞 8자만), 이메일 마스킹
3. **에러는 예외 스택 포함**: `logger.exception()` 사용
4. **보안 이벤트는 WARNING 이상**: 로그인 실패, 토큰 재사용, 권한 없는 접근
5. **운영: JSON (`LOG_JSON=true`)**, 개발: 콘솔 포맷 (`LOG_JSON=false`)

**환경변수 설정:**

```python
# core/config.py (SPECS-BACKEND.md §1.2 참조)
class Settings(BaseSettings):
    LOG_LEVEL: str = "INFO"
    LOG_JSON: bool = True  # 운영: True, 개발: False
```

**금지 사항:**

| 항목 | 이유 |
|------|------|
| `print()` 사용 | 로그 레벨 제어 불가, 구조화 불가 |
| 비밀번호/토큰 전체 값 로깅 | 보안 위험 (로그 파일 노출 시 인증 정보 탈취) |
| PII (email, 전화번호) 평문 로깅 | GDPR/개인정보보호법 위반 가능 |
| 과도한 DEBUG 로그 (운영) | 디스크 사용량 증가, 성능 저하 |

**참조:**
- AuthService 로깅 예시: [SPECS-BACKEND.md §3.3](./SPECS-BACKEND.md#33-authservice)
- Settings 필드: [SPECS-BACKEND.md §1.2](./SPECS-BACKEND.md#12-settings)
