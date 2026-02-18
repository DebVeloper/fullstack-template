# Frontend Reference Specifications

> 이 문서는 Frontend에서 사용하는 **참조 구현 코드**를 모아둔 것입니다.
> 규칙과 컨벤션은 [CONVENTIONS-FRONTEND.md](./CONVENTIONS-FRONTEND.md)를 참조하세요.

---

## 1. Core

### 1.1 BFF 프록시

BFF 프록시는 Backend에서 401 응답을 받으면 자동으로 토큰 갱신을 시도합니다 (Silent Refresh). 갱신 성공 시 새 쿠키를 설정하고 원래 요청을 재시도합니다. 갱신 실패 시 쿠키를 삭제하고 401을 클라이언트에 전달합니다. 동시 다중 요청 시 refresh는 한 번만 실행됩니다 (Promise 캐싱).

**BFF 경로 변환 규칙:**

openapi-ts SDK가 생성하는 경로에는 `/v1/` prefix가 포함되므로(OpenAPI 스펙 기준), BFF 프록시는 `/api/` 이후의 전체 경로를 그대로 Backend에 전달합니다.

| 클라이언트 요청 (SDK) | BFF 캡처 (path) | Backend 도착 |
|---|---|---|
| `GET /api/v1/users/me` | `v1/users/me` | `BACKEND_URL/api/v1/users/me` |
| `POST /api/v1/users` | `v1/users` | `BACKEND_URL/api/v1/users` |
| `GET /api/v1/users?page=1` | `v1/users` + `?page=1` | `BACKEND_URL/api/v1/users?page=1` |

인증 전용 라우트(`/api/auth/*`)는 `[...path]` catch-all에 도달하기 전에 전용 Route Handler(`/api/auth/google/login/route.ts`, `/api/auth/refresh/route.ts` 등)가 먼저 매칭됩니다.

**401 처리 전략 (2단계):**

| 단계 | 위치 | 동작 | 조건 |
|------|------|------|------|
| 1차 | BFF 프록시 (서버 측) | Silent Refresh 시도 → 성공 시 새 쿠키 설정 + 원래 요청 재시도 | refresh_token 쿠키 존재 |
| 2차 | QueryClient (클라이언트 측) | `/login` 리다이렉트 | BFF가 401을 그대로 전달한 경우 (refresh 실패 또는 refresh_token 없음) |

클라이언트에 401이 도달하는 것은 "refresh도 실패한, 완전히 인증이 만료된 상황"만 해당합니다.

```typescript
// frontend/src/app/api/[...path]/route.ts
import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";
import { clearAuthCookies, setAuthCookies } from "@/lib/auth-cookies";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://backend:8000";

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
// NOTE: 서버리스 환경(Vercel)에서는 각 요청이 별도 인스턴스에서 실행될 수 있어
// 이 모듈 레벨 변수는 인스턴스 간 공유되지 않습니다.
// 같은 인스턴스 내 동시 요청에 대한 dedup 역할만 수행합니다.
// 이는 의도된 설계이며, 다른 인스턴스의 중복 refresh는 Token Rotation으로 안전하게 처리됩니다.
// NOTE: Backend의 refresh rotation에 10초 grace period가 적용되어 있어,
// 서버리스 환경에서 여러 인스턴스가 동시에 같은 refresh_token으로 요청하더라도
// grace period 내에는 정상 처리됩니다 (AUTH.md §4.4 참조).
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
  const path = req.nextUrl.pathname.replace(/^\/api\//, "");
  const search = req.nextUrl.search;
  const url = `${BACKEND_URL}/api/${path}${search}`;
  // openapi-ts SDK가 /api/v1/ prefix를 포함하므로
  // catch-all path = "v1/users" → Backend URL = "BACKEND_URL/api/v1/users"

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
          setAuthCookies(cookieStore, {
            access_token: result.accessToken,
            refresh_token: result.refreshToken,
          });

          // 새 access_token으로 원래 요청 재시도
          headers.set("Authorization", `Bearer ${result.accessToken}`);
          response = await fetch(url, {
            method: req.method,
            headers,
            body: bodyBuffer,
          });

          // 재시도 후에도 401이면 쿠키 삭제 (사용자 비활성화 등의 사유)
          if (response.status === 401) {
            clearAuthCookies(cookieStore);
          }
        } else {
          // refresh 실패 → 쿠키 삭제, 401 그대로 전달
          clearAuthCookies(cookieStore);
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

### 1.2 쿠키 헬퍼

인증 쿠키 설정/삭제를 단일 함수로 추출하여 BFF 라우트 간 중복을 제거합니다.

```typescript
// src/lib/auth-cookies.ts
const IS_PRODUCTION = process.env.NODE_ENV === "production";

const ACCESS_TOKEN_MAX_AGE_SECONDS = 60 * 15;
const REFRESH_TOKEN_MAX_AGE_SECONDS = 60 * 60 * 24 * 7;

interface AuthTokens {
  access_token: string;
  refresh_token: string;
}

type CookieStore = Pick<
  Awaited<ReturnType<typeof import("next/headers").cookies>>,
  "set"
>;

interface AuthCookieOptions {
  httpOnly: true;
  secure: boolean;
  sameSite: "lax";
  path: string;
  maxAge: number;
}

const ACCESS_TOKEN_COOKIE_OPTIONS: AuthCookieOptions = {
  httpOnly: true,
  secure: IS_PRODUCTION,
  sameSite: "lax",
  path: "/",
  maxAge: ACCESS_TOKEN_MAX_AGE_SECONDS
};

const REFRESH_TOKEN_COOKIE_OPTIONS: AuthCookieOptions = {
  httpOnly: true,
  secure: IS_PRODUCTION,
  sameSite: "lax",
  path: "/api",
  maxAge: REFRESH_TOKEN_MAX_AGE_SECONDS
};

const CLEAR_ACCESS_TOKEN_COOKIE_OPTIONS: AuthCookieOptions = {
  ...ACCESS_TOKEN_COOKIE_OPTIONS,
  maxAge: 0
};

const CLEAR_REFRESH_TOKEN_COOKIE_OPTIONS: AuthCookieOptions = {
  ...REFRESH_TOKEN_COOKIE_OPTIONS,
  maxAge: 0
};

export function setAuthCookies(cookieStore: CookieStore, tokens: AuthTokens): void {
  cookieStore.set("access_token", tokens.access_token, ACCESS_TOKEN_COOKIE_OPTIONS);
  cookieStore.set("refresh_token", tokens.refresh_token, REFRESH_TOKEN_COOKIE_OPTIONS);
}

export function clearAuthCookies(cookieStore: CookieStore): void {
  cookieStore.set("access_token", "", CLEAR_ACCESS_TOKEN_COOKIE_OPTIONS);
  cookieStore.set("refresh_token", "", CLEAR_REFRESH_TOKEN_COOKIE_OPTIONS);
}
```

### 1.3 BFF 인증 라우트

Backend는 JSON body로 토큰을 반환하고, BFF가 쿠키를 설정합니다. 클라이언트에는 토큰을 노출하지 않습니다. 모든 라우트에서 [§1.2 쿠키 헬퍼](#12-쿠키-헬퍼)를 사용합니다. 쿠키 전략 상세는 [AUTH.md §5](./AUTH.md#5-쿠키-전략)를 참조하세요.

#### Google OAuth Login

- 구현: `src/app/api/auth/google/login/route.ts`
- 동작: state + PKCE(code_verifier) 생성 → 임시 httpOnly 쿠키 저장 → Google authorize로 redirect
- callbackUrl: 상대경로만 허용 (open redirect 차단)

#### Google OAuth Callback

- 구현: `src/app/api/auth/google/callback/route.ts`
- 동작: state/code_verifier 검증 → Backend `/api/v1/auth/google/exchange` 호출 → 토큰 수신 → 쿠키 설정 → callbackUrl(or `/dashboard`) redirect

#### Refresh

```typescript
// src/app/api/auth/refresh/route.ts
import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";
import { clearAuthCookies, setAuthCookies } from "@/lib/auth-cookies";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

interface BackendTokenResponse {
  access_token: string;
  refresh_token: string;
}

export async function POST(request: NextRequest): Promise<NextResponse> {
  void request;
  const cookieStore = await cookies();
  const refreshToken = cookieStore.get("refresh_token")?.value;

  if (!refreshToken) {
    clearAuthCookies(cookieStore);
    return NextResponse.json(
      {
        error: {
          code: "UNAUTHORIZED",
          message: "No refresh token",
          details: null
        }
      },
      { status: 401 }
    );
  }

  const response = await fetch(`${BACKEND_URL}/api/v1/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken })
  });

  if (!response.ok) {
    clearAuthCookies(cookieStore);
    const error = await response.json();
    return NextResponse.json(error, { status: response.status });
  }

  const tokens = (await response.json()) as BackendTokenResponse;
  setAuthCookies(cookieStore, {
    access_token: tokens.access_token,
    refresh_token: tokens.refresh_token
  });

  return NextResponse.json({ token_type: "bearer" });
}
```

#### Logout

```typescript
// src/app/api/auth/logout/route.ts
import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";
import { clearAuthCookies } from "@/lib/auth-cookies";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

export async function POST(request: NextRequest): Promise<NextResponse> {
  void request;
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

  clearAuthCookies(cookieStore);

  return new NextResponse(null, { status: 204 });
}
```

#### (E2E only) Test Login

```typescript
// src/app/api/auth/test-login/route.ts
import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";

import { setAuthCookies } from "@/lib/auth-cookies";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

interface TestLoginRequestBody {
  email: string;
  name?: string;
}

interface BackendTokenResponse {
  access_token: string;
  refresh_token: string;
}

export async function POST(request: NextRequest): Promise<NextResponse> {
  if (process.env.AUTH_TEST_MODE !== "true") {
    return NextResponse.json(
      {
        error: {
          code: "NOT_FOUND",
          message: "Not found",
          details: null
        }
      },
      { status: 404 }
    );
  }

  const configuredSecret = process.env.AUTH_TEST_SECRET;
  if (!configuredSecret) {
    return NextResponse.json(
      {
        error: {
          code: "CONFIGURATION_ERROR",
          message: "Missing AUTH_TEST_SECRET",
          details: null
        }
      },
      { status: 500 }
    );
  }

  const body = (await request.json()) as TestLoginRequestBody;

  let response: Response;
  try {
    response = await fetch(`${BACKEND_URL}/api/v1/auth/test-login`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "x-test-auth-secret": configuredSecret
      },
      body: JSON.stringify({ email: body.email, name: body.name })
    });
  } catch {
    return NextResponse.json(
      {
        error: {
          code: "BAD_GATEWAY",
          message: "Backend service unavailable",
          details: null
        }
      },
      { status: 502 }
    );
  }

  if (!response.ok) {
    const error = await response.json();
    return NextResponse.json(error, { status: response.status });
  }

  const tokens = (await response.json()) as BackendTokenResponse;
  const cookieStore = await cookies();
  setAuthCookies(cookieStore, {
    access_token: tokens.access_token,
    refresh_token: tokens.refresh_token
  });

  return new NextResponse(null, { status: 204 });
}
```

**Auth 이후 사용자 정보 획득 흐름:**

1. `/api/auth/google/callback` (BFF) 성공 → 쿠키 설정 완료, `/dashboard`로 redirect
2. TanStack Query가 `GET /api/v1/users/me` 요청 (openapi-ts SDK)
3. Next.js BFF catch-all(`/api/[...path]`)이 Backend로 프록시

### 1.4 Query Key Factory

```typescript
// hooks/queries/keys.ts
const usersRootKey = ["users"] as const;
const adminUsersRootKey = ["admin-users"] as const;
const adminUsersListKey = [...adminUsersRootKey, "list"] as const;

export interface AdminUsersListQuery {
  page: number;
  size: number;
  include_deleted: boolean;
}

export const userKeys = {
  all: usersRootKey,
  me: () => [...usersRootKey, "me"] as const
};

export const adminUserKeys = {
  all: adminUsersRootKey,
  lists: () => adminUsersListKey,
  list: (query: AdminUsersListQuery) => [...adminUsersListKey, query] as const
};
```

```typescript
// hooks/queries/use-current-user.ts
import { useQuery } from "@tanstack/react-query";

import { getApiV1UsersMe as getMe } from "@/client/sdk.gen";
import { apiClient } from "@/lib/api-client";

import { userKeys } from "./keys";

const CURRENT_USER_STALE_TIME = 60_000;

export function useCurrentUser() {
  return useQuery({
    queryKey: userKeys.me(),
    queryFn: () => getMe({ client: apiClient }),
    staleTime: CURRENT_USER_STALE_TIME
  });
}
```

### 1.5 Custom Hook 패턴

openapi-ts SDK와 연결하는 Custom Hook 패턴은 [§2.3 SDK → TanStack Query 연결 패턴](#23-sdk--tanstack-query-연결-패턴)을 참조하세요.

### 1.6 cn() 유틸리티

```typescript
// lib/utils.ts
import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

### 1.7 인증 미들웨어

```typescript
// src/middleware.ts
import { NextRequest, NextResponse } from "next/server";

const DEFAULT_AUTHENTICATED_REDIRECT_PATH = "/dashboard";
const LOGIN_PATH = "/login";
const PUBLIC_ROUTES = new Set(["/", LOGIN_PATH]);

function isPublicRoute(pathname: string): boolean {
  return PUBLIC_ROUTES.has(pathname);
}

function sanitizeCallbackUrl(callbackUrl: string): string {
  const normalized = callbackUrl.trim();

  if (!normalized) {
    return DEFAULT_AUTHENTICATED_REDIRECT_PATH;
  }

  try {
    const parsedUrl = new URL(normalized, "http://localhost");

    if (parsedUrl.origin !== "http://localhost") {
      return DEFAULT_AUTHENTICATED_REDIRECT_PATH;
    }

    if (!parsedUrl.pathname.startsWith("/")) {
      return DEFAULT_AUTHENTICATED_REDIRECT_PATH;
    }

    if (parsedUrl.pathname.startsWith("//")) {
      return DEFAULT_AUTHENTICATED_REDIRECT_PATH;
    }

    return `${parsedUrl.pathname}${parsedUrl.search}${parsedUrl.hash}`;
  } catch {
    return DEFAULT_AUTHENTICATED_REDIRECT_PATH;
  }
}

export function middleware(request: NextRequest): NextResponse {
  const accessToken = request.cookies.get("access_token")?.value;
  const { pathname, search } = request.nextUrl;

  if (pathname === LOGIN_PATH && accessToken) {
    return NextResponse.redirect(
      new URL(DEFAULT_AUTHENTICATED_REDIRECT_PATH, request.url)
    );
  }

  if (isPublicRoute(pathname)) {
    return NextResponse.next();
  }

  if (!accessToken) {
    const callbackUrl = sanitizeCallbackUrl(`${pathname}${search}`);
    const loginUrl = new URL(LOGIN_PATH, request.url);
    loginUrl.searchParams.set("callbackUrl", callbackUrl);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|api/).*)"]
};
```

### 1.8 테스트 Wrapper

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

/** renderHook용 wrapper 생성 함수 */
export function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });

  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  };
}
```

### 1.9 BFF 프록시 테스트

BFF 프록시의 핵심 동작(인증 헤더 전달, Silent Refresh, 에러 전달)을 vitest로 테스트합니다. Backend는 MSW로 모킹합니다.

```typescript
// src/tests/bff-proxy.test.ts
import { describe, it, expect, beforeAll, afterAll, afterEach, vi } from "vitest";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { NextRequest } from "next/server";

const BACKEND_URL = "http://backend:8000";
const server = setupServer();

// next/headers 모킹 — cookies() 반환값 제어
const mockCookieStore = {
  get: vi.fn(),
  set: vi.fn(),
  delete: vi.fn(),
};

vi.mock("next/headers", () => ({
  cookies: vi.fn(() => Promise.resolve(mockCookieStore)),
}));

function createMockRequest(
  path: string,
  options: { method?: string; body?: unknown } = {},
): NextRequest {
  const { method = "GET", body } = options;
  const init: RequestInit = { method };
  if (body) {
    init.body = JSON.stringify(body);
    init.headers = { "Content-Type": "application/json" };
  }
  return new NextRequest(`http://localhost:3000/api${path}`, init);
}

beforeAll(() => server.listen());
afterEach(() => {
  server.resetHandlers();
  vi.clearAllMocks();
});
afterAll(() => server.close());

describe("BFF Proxy", () => {
  it("should forward authorization header from cookie", async () => {
    mockCookieStore.get.mockImplementation((name: string) => {
      if (name === "access_token") return { value: "test-access-token" };
      return undefined;
    });

    let capturedAuth: string | null = null;
    server.use(
      http.get(`${BACKEND_URL}/api/v1/users/me`, ({ request }) => {
        capturedAuth = request.headers.get("Authorization");
        return HttpResponse.json({ id: "1", email: "test@test.com" });
      }),
    );

    const { GET } = await import("@/app/api/[...path]/route");
    const req = createMockRequest("/users/me");
    const response = await GET(req);

    expect(response.status).toBe(200);
    expect(capturedAuth).toBe("Bearer test-access-token");
  });

  it("should attempt silent refresh on 401", async () => {
    mockCookieStore.get.mockImplementation((name: string) => {
      if (name === "access_token") return { value: "expired-token" };
      if (name === "refresh_token") return { value: "valid-refresh-token" };
      return undefined;
    });

    let refreshCalled = false;
    server.use(
      http.get(`${BACKEND_URL}/api/v1/users/me`, () => {
        return HttpResponse.json(
          { error: { code: "UNAUTHORIZED", message: "Expired" } },
          { status: 401 },
        );
      }),
      http.post(`${BACKEND_URL}/api/v1/auth/refresh`, () => {
        refreshCalled = true;
        return HttpResponse.json({
          access_token: "new-access-token",
          refresh_token: "new-refresh-token",
        });
      }),
    );

    const { GET } = await import("@/app/api/[...path]/route");
    const req = createMockRequest("/users/me");
    await GET(req);

    expect(refreshCalled).toBe(true);
    expect(mockCookieStore.set).toHaveBeenCalledWith(
      "access_token",
      "new-access-token",
      expect.objectContaining({ httpOnly: true }),
    );
  });

  it("should return 502 when backend is unavailable", async () => {
    mockCookieStore.get.mockReturnValue(undefined);
    server.use(
      http.get(`${BACKEND_URL}/api/v1/users/me`, () => {
        return HttpResponse.error();
      }),
    );

    const { GET } = await import("@/app/api/[...path]/route");
    const req = createMockRequest("/users/me");
    const response = await GET(req);

    expect(response.status).toBe(502);
    const body = await response.json();
    expect(body.error.code).toBe("BAD_GATEWAY");
  });
});
```

**테스트 전략:**
- MSW로 Backend 응답 모킹 (네트워크 레벨 인터셉트)
- NextRequest 직접 생성: `new NextRequest(url, init)`
- next/headers 모킹: `vi.mock("next/headers")` + mockCookieStore
- Route Handler dynamic import: `await import("@/app/api/[...path]/route")`
- 쿠키 검증: `mockCookieStore.set` 호출 확인

### 1.10 Root Layout

```typescript
// frontend/src/app/layout.tsx
import type { Metadata } from "next";
import { Toaster } from "sonner";
import { Providers } from "./providers";
import "@/app/globals.css";

export const metadata: Metadata = {
  title: { default: "App", template: "%s | App" },
  description: "Fullstack Template",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko" suppressHydrationWarning>
      <body>
        <Providers>{children}</Providers>
        <Toaster position="top-right" richColors />
      </body>
    </html>
  );
}
```

```typescript
// frontend/src/app/providers.tsx
"use client";

import { QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { useState } from "react";
import { createQueryClient } from "@/lib/query-client";

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(() => createQueryClient());

  return (
    <QueryClientProvider client={queryClient}>
      {children}
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  );
}
```

### 1.11 에러/로딩 UI

#### error.tsx (글로벌 에러 바운더리)

```typescript
// src/app/error.tsx
"use client";

interface ErrorPageProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function Error({ error, reset }: ErrorPageProps) {
  return (
    <div className="flex min-h-[400px] flex-col items-center justify-center gap-4">
      <h2 className="text-xl font-semibold">문제가 발생했습니다</h2>
      <p className="text-muted-foreground">{error.message}</p>
      <button
        onClick={reset}
        className="rounded-md bg-primary px-4 py-2 text-primary-foreground hover:bg-primary/90"
      >
        다시 시도
      </button>
    </div>
  );
}
```

#### loading.tsx (글로벌 로딩)

```typescript
// src/app/loading.tsx
import { Skeleton } from "@/components/ui/skeleton";

export default function Loading() {
  return (
    <div className="space-y-4 p-6">
      <Skeleton className="h-8 w-1/3" />
      <Skeleton className="h-4 w-2/3" />
      <Skeleton className="h-4 w-1/2" />
      <div className="grid grid-cols-3 gap-4 pt-4">
        <Skeleton className="h-32" />
        <Skeleton className="h-32" />
        <Skeleton className="h-32" />
      </div>
    </div>
  );
}
```

### 1.12 Google OAuth Login (UI)

이 템플릿은 이메일/비밀번호 폼을 제공하지 않고 **Google OAuth(OIDC) 로그인만** 제공합니다.

- `/login`: Google 로그인 시작(`/api/auth/google/login`) 링크 렌더
- `/api/auth/google/login`: state + PKCE 생성 → Google authorize redirect
- `/api/auth/google/callback`: Backend `/api/v1/auth/google/exchange` 호출 → 쿠키 설정 → redirect

```typescript
// src/app/(public)/login/page.tsx
import Link from "next/link";
import type { ReactElement } from "react";

interface LoginPageProps {
  searchParams: Promise<{
    callbackUrl?: string | string[];
  }>;
}

export default async function LoginPage({
  searchParams
}: LoginPageProps): Promise<ReactElement> {
  const resolvedSearchParams = await searchParams;
  const callbackUrlParam = Array.isArray(resolvedSearchParams.callbackUrl)
    ? resolvedSearchParams.callbackUrl[0]
    : resolvedSearchParams.callbackUrl;

  const googleLoginHref = callbackUrlParam
    ? `/api/auth/google/login?callbackUrl=${encodeURIComponent(callbackUrlParam)}`
    : "/api/auth/google/login";

  return (
    <main className="page-shell">
      <section className="login-content" aria-labelledby="login-title">
        <h1 id="login-title">Sign in</h1>
        <p>Continue with your Google account to access the dashboard.</p>
        <Link
          href={googleLoginHref}
          className="cta-button"
          aria-label="Continue with Google"
        >
          Continue with Google
        </Link>
      </section>
    </main>
  );
}
```

**Auth 요청 규칙:**
- Google OAuth(login/callback), refresh/logout, test-login은 **BFF 전용 라우트**(`/api/auth/*`)를 사용합니다 (SDK 금지)
- openapi-ts SDK는 **인증된 일반 API 요청**(`/api/v1/*`)에만 사용합니다 → BFF catch-all(`/api/[...path]`)이 프록시

### 1.13 테스트 설정 + 훅 테스트

#### 테스트 설정

```typescript
// src/tests/setup.ts
import "@testing-library/jest-dom/vitest";
```

#### 훅 테스트 예시

```typescript
// src/hooks/queries/__tests__/use-current-user.test.ts
import { renderHook, waitFor } from "@testing-library/react";
import { createWrapper } from "@/tests/utils";
import { useCurrentUser } from "../use-current-user";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";

const server = setupServer();
beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe("useCurrentUser", () => {
  it("should fetch current user data", async () => {
    server.use(
      http.get("/api/v1/users/me", () =>
        HttpResponse.json({ id: "1", email: "test@test.com", name: "Test" }),
      ),
    );
    const { result } = renderHook(() => useCurrentUser(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.email).toBe("test@test.com");
  });
});
```

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

> **경로 매핑:** openapi-ts는 Backend OpenAPI 스펙의 경로를 그대로 사용합니다 (예: `/api/v1/users`).
> SDK 함수 호출 시 이 경로가 `baseUrl`과 결합됩니다. `baseUrl: ""`(빈 문자열)로 설정하여
> SDK가 `/api/v1/users`로 요청하면, Next.js catch-all 라우트가 이를 캡처하여 Backend로 프록시합니다.
> 자세한 경로 변환은 [§1.1 BFF 프록시](./SPECS-FRONTEND.md#11-bff-프록시)를 참조하세요.

### 2.2 API 클라이언트 설정

```typescript
// frontend/src/lib/api-client.ts
import { createClient } from "@hey-api/client-fetch";
import { ApiError } from "./api-error";

export const apiClient = createClient({
  baseUrl: "",   // SDK가 생성하는 경로에 /api/v1/ prefix가 포함됨 → BFF catch-all이 처리
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
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
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

Auth 요청 규칙(BFF fetch, SDK 미사용)은 [CONVENTIONS-FRONTEND.md §6](./CONVENTIONS-FRONTEND.md#6-openapi-ts-api-클라이언트)를 참조하세요.

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
import { QueryCache, QueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { ApiError } from "./api-error";

export function createQueryClient() {
  return new QueryClient({
    queryCache: new QueryCache({
      onError: (error) => {
        if (error instanceof ApiError && error.status === 401) {
          if (typeof window !== "undefined") {
            window.location.replace("/login");
          }
          return;
        }
        // queries 에러는 컴포넌트 error boundary에서 처리하므로
        // 여기서는 401 리다이렉트만 담당
      },
    }),
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

### 3.4 에러 코드 → 사용자 메시지 매핑

Backend 에러 코드를 한국어 사용자 메시지로 변환합니다. Backend의 `error.message`는 개발자용 영어 메시지이므로, Frontend에서 에러 코드 기반으로 사용자 친화적 메시지를 결정합니다.

```typescript
// src/lib/error-messages.ts
const ERROR_MESSAGES: Record<string, string> = {
  BAD_REQUEST: "잘못된 요청입니다.",
  UNAUTHORIZED: "인증이 만료되었습니다. 다시 로그인해주세요.",
  FORBIDDEN: "접근 권한이 없습니다.",
  NOT_FOUND: "요청한 리소스를 찾을 수 없습니다.",
  CONFLICT: "이미 존재하는 데이터입니다.",
  VALIDATION_ERROR: "입력 데이터를 확인해주세요.",
  RATE_LIMIT_EXCEEDED: "요청이 너무 많습니다. 잠시 후 다시 시도해주세요.",
  INTERNAL_ERROR: "서버 오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
  BAD_GATEWAY: "서비스에 연결할 수 없습니다. 잠시 후 다시 시도해주세요.",
};

export function getErrorMessage(code: string, fallback?: string): string {
  return ERROR_MESSAGES[code] ?? fallback ?? "오류가 발생했습니다.";
}
```

**사용 예시 (mutation onError):**

```typescript
import { getErrorMessage } from "@/lib/error-messages";

onError: (error) => {
  if (error instanceof ApiError) {
    toast.error(getErrorMessage(error.code, error.message));
  }
}
```
