# Infra (`infra/`)

로컬 개발용 Postgres/Redis를 docker compose로 제공.

## Where To Look

- Compose entrypoint: `infra/docker-compose.yml`
- Initdb scripts: `infra/initdb/`
- Env defaults: `infra/.env.example`

## Commands

```bash
docker compose -f infra/docker-compose.yml up -d
docker compose -f infra/docker-compose.yml down -v
```

## Notes

- `infra/initdb/001-create-test-db.sh`가 기본 테스트 DB(`POSTGRES_TEST_DB`, default: `app_test`)를 생성한다
- Backend 테스트는 `DATABASE_URL_TEST`로 이 테스트 DB에 연결한다
