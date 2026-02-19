# Generated OpenAPI Client (`frontend/src/client/`)

`openapi-ts`로 자동 생성되는 코드입니다. **수동 수정 금지**.

## Source Of Truth

- Input(OpenAPI): `http://localhost:8000/openapi.json`
- Config: `frontend/openapi-ts.config.ts`
- Output dir: `frontend/src/client/`

## How To Regenerate

```bash
# backend must be running on :8000
cd frontend
pnpm run generate:api
```

## Rules

- Backend의 스키마/`response_model` 변경 시 반드시 재생성 후 diff를 확인한다
- Auth 관련 `/api/auth/*` 라우트는 SDK를 사용하지 않는다 (BFF 전용 라우트)
