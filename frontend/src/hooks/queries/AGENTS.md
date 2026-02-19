# Query Hooks (`frontend/src/hooks/queries/`)

TanStack Query v5 기반의 "서버 상태" 접근 레이어.

## Where To Look

- Query key factory: `frontend/src/hooks/queries/keys.ts`
- Current user query: `frontend/src/hooks/queries/use-current-user.ts`
- Admin users queries/mutations: `frontend/src/hooks/queries/use-admin-users.ts`

## Rules

- 컴포넌트에서 `useQuery`/`useMutation` 직접 호출 금지 → 반드시 이 디렉토리의 커스텀 훅을 통해 접근
- Query key는 factory를 통해서만 생성 (`keys.ts`)
- Mutation 성공 시 관련 query invalidation 필수 (`invalidateQueries`)

## Error Handling

- Generated client 경로는 `frontend/src/lib/api-client.ts` interceptor가 `ApiError`로 변환한다
- 직접 `fetch`를 쓰는 경우에도 `ApiError`/unified error envelope(`{ error: { code, message, details } }`)를 유지한다
