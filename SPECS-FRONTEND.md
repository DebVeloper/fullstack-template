# Frontend Reference Specifications

> 이 문서는 Frontend에서 사용하는 **참조 구현 코드(보일러플레이트)**를 모아둔 것입니다.
> 규칙과 컨벤션은 [CONVENTIONS-FRONTEND.md](./CONVENTIONS-FRONTEND.md)를 참조하세요.

---

## 1. Core

### 1.1 BFF 프록시

BFF 프록시는 Backend에서 401 응답을 받으면 자동으로 토큰 갱신을 시도합니다 (Silent Refresh). 갱신 성공 시 새 쿠키를 설정하고 원래 요청을 재시도합니다. 갱신 실패 시 쿠키를 삭제하고 401을 클라이언트에 전달합니다. 동시 다중 요청 시 refresh는 한 번만 실행됩니다 (Promise 캐싱).

```typescript
// frontend/src/app/api/[...path]/route.ts
import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://backend:8000";
const IS_PRODUCTION = process.env.NODE_ENV === "production";

const HOP_BY_HOP_HEADERS = new Set([
  "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
  "te", "trailers", "transfer-encoding", "upgrade",
]);

function filterHeaders(headers: Headers): Headers {
  const filtered = new Headers();
  headers.forEach((value, key) => {
    if (!HOP_BY_HOP_HEADERS.has(key.toLowerCase())) {
      filtered.set(key, value);
    }
  });
  return filtered;
}

// Silent Refresh 동시성 제어
let refreshPromise: Promise<RefreshResult> | null = null;

interface RefreshResult {
  success: boolean;
  accessToken?: string;
  refreshToken?: string;
}

async function refreshTokens(currentRefreshToken: string): Promise<RefreshResult> {
  if (refreshPromise) {
    return refreshPromise;
  }

  refreshPromise = (async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/v1/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: currentRefreshToken }),
      });

      if (!response.ok) {
        return { success: false };
      }

      const tokens = await response.json();
      return {
        success: true,
        accessToken: tokens.access_token,
        refreshToken: tokens.refresh_token,
      };
    } finally {
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}

async function proxyRequest(req: NextRequest) {
  const path = req.nextUrl.pathname.replace(/^\/api/, "");
  const url = `${BACKEND_URL}/api/v1${path}${req.nextUrl.search}`;

  const cookieStore = await cookies();
  const accessToken = cookieStore.get("access_token")?.value;

  const headers = new Headers(req.headers);
  headers.delete("host");
  if (accessToken) {
    headers.set("Authorization", `Bearer ${accessToken}`);
  }

  // 요청 body를 재사용 가능하도록 버퍼링
  let bodyBuffer: ArrayBuffer | null = null;
  if (req.method !== "GET" && req.method !== "HEAD") {
    bodyBuffer = await req.arrayBuffer();
  }

  try {
    let response = await fetch(url, {
      method: req.method,
      headers,
      body: bodyBuffer,
    });

    // 401이고 refresh_token이 있으면 자동 갱신 시도
    if (response.status === 401) {
      const refreshToken = cookieStore.get("refresh_token")?.value;
      if (refreshToken) {
        const result = await refreshTokens(refreshToken);

        if (result.success && result.accessToken && result.refreshToken) {
          cookieStore.set("access_token", result.accessToken, {
            httpOnly: true,
            secure: IS_PRODUCTION,
            sameSite: "lax",
            path: "/",
            maxAge: 900,
          });
          cookieStore.set("refresh_token", result.refreshToken, {
            httpOnly: true,
            secure: IS_PRODUCTION,
            sameSite: "lax",
            path: "/api/auth",
            maxAge: 604800,
          });

          // 새 access_token으로 원래 요청 재시도
          headers.set("Authorization", `Bearer ${result.accessToken}`);
          response = await fetch(url, {
            method: req.method,
            headers,
            body: bodyBuffer,
          });
        } else {
          // refresh 실패 → 쿠키 삭제, 401 그대로 전달
          cookieStore.delete("access_token");
          cookieStore.delete("refresh_token");
        }
      }
    }

    return new NextResponse(response.body, {
      status: response.status,
      headers: filterHeaders(response.headers),
    });
  } catch (error) {
    return NextResponse.json(
      { error: { code: "BAD_GATEWAY", message: "Backend service unavailable", details: null } },
      { status: 502 },
    );
  }
}

export const GET = proxyRequest;
export const POST = proxyRequest;
export const PATCH = proxyRequest;
export const DELETE = proxyRequest;
```

### 1.2 BFF 인증 라우트

Backend는 JSON body로 토큰을 반환하고, BFF가 쿠키를 설정합니다. 클라이언트에는 토큰을 노출하지 않습니다.

```typescript
// frontend/src/app/api/auth/login/route.ts
import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://backend:8000";
const IS_PRODUCTION = process.env.NODE_ENV === "production";

export async function POST(req: NextRequest) {
  const body = await req.json();

  const response = await fetch(`${BACKEND_URL}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const error = await response.json();
    return NextResponse.json(error, { status: response.status });
  }

  const data = await response.json();
  const cookieStore = await cookies();

  cookieStore.set("access_token", data.access_token, {
    httpOnly: true,
    secure: IS_PRODUCTION,
    sameSite: "lax",
    path: "/",
    maxAge: 900,
  });

  cookieStore.set("refresh_token", data.refresh_token, {
    httpOnly: true,
    secure: IS_PRODUCTION,
    sameSite: "lax",
    path: "/api/auth",
    maxAge: 604800,
  });

  return NextResponse.json({ token_type: "bearer" });
}
```

```typescript
// frontend/src/app/api/auth/refresh/route.ts
import { cookies } from "next/headers";
import { NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://backend:8000";
const IS_PRODUCTION = process.env.NODE_ENV === "production";

export async function POST() {
  const cookieStore = await cookies();
  const refreshToken = cookieStore.get("refresh_token")?.value;

  if (!refreshToken) {
    return NextResponse.json(
      { error: { code: "UNAUTHORIZED", message: "No refresh token", details: null } },
      { status: 401 },
    );
  }

  const response = await fetch(`${BACKEND_URL}/api/v1/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });

  if (!response.ok) {
    cookieStore.delete("access_token");
    cookieStore.delete("refresh_token");
    const error = await response.json();
    return NextResponse.json(error, { status: response.status });
  }

  const data = await response.json();

  cookieStore.set("access_token", data.access_token, {
    httpOnly: true,
    secure: IS_PRODUCTION,
    sameSite: "lax",
    path: "/",
    maxAge: 900,
  });

  cookieStore.set("refresh_token", data.refresh_token, {
    httpOnly: true,
    secure: IS_PRODUCTION,
    sameSite: "lax",
    path: "/api/auth",
    maxAge: 604800,
  });

  return NextResponse.json({ token_type: "bearer" });
}
```

```typescript
// frontend/src/app/api/auth/logout/route.ts
import { cookies } from "next/headers";
import { NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://backend:8000";

export async function POST() {
  const cookieStore = await cookies();
  const refreshToken = cookieStore.get("refresh_token")?.value;

  if (refreshToken) {
    await fetch(`${BACKEND_URL}/api/v1/auth/logout`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    }).catch(() => {
      // Backend 실패해도 쿠키는 삭제
    });
  }

  cookieStore.delete("access_token");
  cookieStore.delete("refresh_token");

  return new NextResponse(null, { status: 204 });
}
```

### 1.3 Query Key Factory

```typescript
// hooks/queries/keys.ts
export const userKeys = {
  all: ["users"] as const,
  lists: () => [...userKeys.all, "list"] as const,
  list: (params: UserListParams) => [...userKeys.lists(), params] as const,
  details: () => [...userKeys.all, "detail"] as const,
  detail: (id: string) => [...userKeys.details(), id] as const,
};
```

### 1.4 Custom Hook 패턴

```typescript
// hooks/queries/use-users.ts
export function useUsers(params: UserListParams) {
  return useQuery({
    queryKey: userKeys.list(params),
    queryFn: () => getUsers(params),
  });
}

export function useCreateUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createUser,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: userKeys.lists() });
    },
  });
}
```

### 1.5 cn() 유틸리티

```typescript
// lib/utils.ts
import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

### 1.6 테스트 Wrapper

```typescript
// src/tests/utils.tsx
export function renderWithProviders(
  ui: ReactElement,
  options?: Omit<RenderOptions, "wrapper">,
) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });

  function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  }

  return render(ui, { wrapper: Wrapper, ...options });
}
```

### 1.7 인증 미들웨어

```typescript
// frontend/src/middleware.ts
import { NextRequest, NextResponse } from "next/server";

// 미인증 사용자도 접근 가능한 공개 라우트 (화이트리스트)
const PUBLIC_ROUTES = ["/", "/login", "/register", "/about"];

// 로그인 사용자가 접근하면 /dashboard로 리다이렉트할 라우트
const AUTH_REDIRECT_ROUTES = ["/login", "/register"];

function isPublicRoute(pathname: string): boolean {
  return PUBLIC_ROUTES.some(
    (route) => pathname === route || pathname.startsWith(`${route}/`),
  );
}

export function middleware(req: NextRequest) {
  const accessToken = req.cookies.get("access_token")?.value;
  const { pathname } = req.nextUrl;

  // 공개 라우트가 아닌 모든 라우트는 인증 필요 (기본 보호)
  if (!isPublicRoute(pathname) && !accessToken) {
    const loginUrl = new URL("/login", req.url);
    loginUrl.searchParams.set("callbackUrl", `${pathname}${req.nextUrl.search}`);
    return NextResponse.redirect(loginUrl);
  }

  // 로그인된 사용자가 인증 전용 라우트 접근 → /dashboard 리다이렉트
  if (accessToken && AUTH_REDIRECT_ROUTES.some((route) => pathname === route)) {
    return NextResponse.redirect(new URL("/dashboard", req.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    // static files, _next, api 제외
    "/((?!_next/static|_next/image|favicon.ico|api/).*)",
  ],
};
```

### 1.8 BFF 프록시 테스트

BFF 프록시의 핵심 동작(인증 헤더 전달, Silent Refresh, 에러 전달)을 vitest로 테스트합니다. Backend는 MSW로 모킹합니다.

```typescript
// src/tests/bff-proxy.test.ts
import { describe, it, expect, beforeAll, afterAll, afterEach } from "vitest";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";

const BACKEND_URL = "http://backend:8000";

const server = setupServer();

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe("BFF Proxy", () => {
  it("should forward authorization header from cookie", async () => {
    let capturedAuth: string | null = null;
    server.use(
      http.get(`${BACKEND_URL}/api/v1/users/me`, ({ request }) => {
        capturedAuth = request.headers.get("Authorization");
        return HttpResponse.json({ id: "1", email: "test@test.com" });
      }),
    );

    // Route Handler를 직접 import하여 테스트
    // 실제 구현 시 NextRequest 모킹이 필요할 수 있음
    expect(capturedAuth).toBe("Bearer test-token");
  });

  it("should attempt silent refresh on 401", async () => {
    let refreshCalled = false;
    server.use(
      http.get(`${BACKEND_URL}/api/v1/users/me`, () => {
        return HttpResponse.json({}, { status: 401 });
      }),
      http.post(`${BACKEND_URL}/api/v1/auth/refresh`, () => {
        refreshCalled = true;
        return HttpResponse.json({
          access_token: "new-access",
          refresh_token: "new-refresh",
        });
      }),
    );

    // ... 프록시 호출 후
    expect(refreshCalled).toBe(true);
  });

  it("should return 502 when backend is unavailable", async () => {
    server.use(
      http.get(`${BACKEND_URL}/api/v1/users/me`, () => {
        return HttpResponse.error();
      }),
    );

    // ... 프록시 호출 후
    // response.status === 502, body.error.code === "BAD_GATEWAY"
  });
});
```

**테스트 전략:**
- MSW로 Backend 응답 모킹 (네트워크 레벨 인터셉트)
- Next.js Route Handler는 순수 함수로 import하여 테스트
- `NextRequest`/`NextResponse` 모킹: `next/server`에서 직접 생성 가능
- 쿠키 검증: 응답의 `Set-Cookie` 헤더 확인

---

## 2. openapi-ts 연결

Backend의 OpenAPI 스펙에서 타입과 SDK를 자동 생성하고 TanStack Query와 연결합니다.

### 2.1 openapi-ts 설정

```typescript
// frontend/openapi-ts.config.ts
import { defineConfig } from "@hey-api/openapi-ts";

export default defineConfig({
  input: "http://localhost:8000/openapi.json",
  output: "src/client",
  plugins: [
    "@hey-api/typescript",
    "@hey-api/sdk",
    {
      name: "@hey-api/client-fetch",
      runtimeConfigPath: "./src/lib/api-client.ts",
    },
  ],
});
```

### 2.2 API 클라이언트 설정

```typescript
// frontend/src/lib/api-client.ts
import { createClient } from "@hey-api/client-fetch";
import { ApiError } from "./api-error";

export const apiClient = createClient({
  baseUrl: "/api",   // BFF 프록시 경유 — Backend URL 직접 사용 금지
});

// 에러 응답 → ApiError 변환 인터셉터 (throwOnError 대신 사용)
apiClient.interceptors.response.use((response) => {
  if (response.status >= 400) {
    const body = response.data as { error?: { code: string; message: string; details: unknown } };
    if (body?.error) {
      throw new ApiError(response.status, body.error);
    }
    // Backend 에러 포맷이 아닌 경우 (예: BFF 502, nginx 에러)
    throw new ApiError(response.status, {
      code: "UNKNOWN_ERROR",
      message: `Request failed with status ${response.status}`,
      details: null,
    });
  }
  return response;
});
```

### 2.3 SDK → TanStack Query 연결 패턴

```typescript
// hooks/queries/use-users.ts
import { getUsers, createUser } from "@/client/sdk.gen";
import type { GetUsersData } from "@/client/types.gen";
import { userKeys } from "./keys";

export function useUsers(params: GetUsersData["query"]) {
  return useQuery({
    queryKey: userKeys.list(params),
    queryFn: () => getUsers({ query: params }),
  });
}

export function useCreateUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: UserCreate) => createUser({ body: data }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: userKeys.lists() });
    },
  });
}
```

---

## 3. 에러 처리

### 3.1 API 에러 파싱 유틸리티

```typescript
// frontend/src/lib/api-error.ts
interface ApiErrorDetail {
  code: string;
  message: string;
  details: ValidationFieldError[] | null;
}

interface ValidationFieldError {
  field: string;
  message: string;
}

export class ApiError extends Error {
  readonly code: string;
  readonly status: number;
  readonly details: ValidationFieldError[] | null;

  constructor(status: number, error: ApiErrorDetail) {
    super(error.message);
    this.name = "ApiError";
    this.status = status;
    this.code = error.code;
    this.details = error.details as ValidationFieldError[] | null;
  }

  get isValidationError(): boolean {
    return this.code === "VALIDATION_ERROR";
  }

  get fieldErrors(): Record<string, string> {
    if (!this.details) return {};
    return Object.fromEntries(
      this.details.map((d) => [d.field, d.message]),
    );
  }
}

export async function parseApiError(response: Response): Promise<ApiError> {
  const body = await response.json();
  return new ApiError(response.status, body.error);
}
```

### 3.2 TanStack Query 글로벌 에러 핸들러

```typescript
// frontend/src/lib/query-client.ts
import { QueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { ApiError } from "./api-error";

export function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: {
        retry: false,
        onError: (error) => {
          if (error instanceof ApiError) {
            if (error.status === 401) {
              // SSR 환경 guard + SPA 친화적 리다이렉트
              if (typeof window !== "undefined") {
                window.location.replace("/login");
              }
              return;
            }
            toast.error(error.message);
            return;
          }
          toast.error("오류가 발생했습니다.");
        },
      },
    },
  });
}
```

### 3.3 폼 validation 에러 표시 패턴

```typescript
// 사용 예시: 폼 컴포넌트에서 mutation 에러 처리
const mutation = useCreateUser();

async function onSubmit(data: UserCreate) {
  try {
    await mutation.mutateAsync(data);
  } catch (error) {
    if (error instanceof ApiError && error.isValidationError) {
      const fieldErrors = error.fieldErrors;
      Object.entries(fieldErrors).forEach(([field, message]) => {
        form.setError(field as keyof UserCreate, { message });
      });
    }
  }
}
```
