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

인증 전용 라우트(`/api/auth/*`)는 `[...path]` catch-all에 도달하기 전에 전용 Route Handler(`/api/auth/login/route.ts` 등)가 먼저 매칭됩니다.

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

interface AuthTokens {
  access_token: string;
  refresh_token: string;
}

type CookieStore = Awaited<ReturnType<typeof import("next/headers").cookies>>;

export function setAuthCookies(cookieStore: CookieStore, tokens: AuthTokens): void {
  cookieStore.set("access_token", tokens.access_token, {
    httpOnly: true,
    secure: IS_PRODUCTION,
    sameSite: "lax",
    path: "/",
    maxAge: 900,
  });
  cookieStore.set("refresh_token", tokens.refresh_token, {
    httpOnly: true,
    secure: IS_PRODUCTION,
    sameSite: "lax",
    path: "/api/auth",
    maxAge: 604800,
  });
}

export function clearAuthCookies(cookieStore: CookieStore): void {
  cookieStore.delete("access_token");
  cookieStore.delete("refresh_token");
}
```

### 1.3 BFF 인증 라우트

Backend는 JSON body로 토큰을 반환하고, BFF가 쿠키를 설정합니다. 클라이언트에는 토큰을 노출하지 않습니다. 모든 라우트에서 [§1.2 쿠키 헬퍼](#12-쿠키-헬퍼)를 사용합니다. 쿠키 전략 상세는 [AUTH.md §5](./AUTH.md#5-쿠키-전략)를 참조하세요.

#### Login

```typescript
// src/app/api/auth/login/route.ts
import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";
import { setAuthCookies } from "@/lib/auth-cookies";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://backend:8000";

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
  setAuthCookies(cookieStore, data);

  return NextResponse.json({ token_type: "bearer" });
}
```

#### Refresh

```typescript
// src/app/api/auth/refresh/route.ts
import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { clearAuthCookies, setAuthCookies } from "@/lib/auth-cookies";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://backend:8000";

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
    clearAuthCookies(cookieStore);
    const error = await response.json();
    return NextResponse.json(error, { status: response.status });
  }

  const data = await response.json();
  setAuthCookies(cookieStore, data);

  return NextResponse.json({ token_type: "bearer" });
}
```

#### Logout

```typescript
// src/app/api/auth/logout/route.ts
import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { clearAuthCookies } from "@/lib/auth-cookies";

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

  clearAuthCookies(cookieStore);

  return new NextResponse(null, { status: 204 });
}
```

#### Register (자동 로그인)

```typescript
// src/app/api/auth/register/route.ts
import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";
import { setAuthCookies } from "@/lib/auth-cookies";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://backend:8000";

export async function POST(req: NextRequest) {
  const body = await req.json();

  // 1. Backend에 회원가입 요청
  const registerRes = await fetch(`${BACKEND_URL}/api/v1/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!registerRes.ok) {
    const error = await registerRes.json();
    return NextResponse.json(error, { status: registerRes.status });
  }

  // 2. 회원가입 성공 → 자동 로그인 (같은 credentials로 로그인)
  const loginRes = await fetch(`${BACKEND_URL}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: body.email, password: body.password }),
  });

  if (!loginRes.ok) {
    // 회원가입은 성공했지만 자동 로그인 실패 — 사용자에게 로그인 페이지 안내
    return NextResponse.json({ registered: true, autoLogin: false }, { status: 201 });
  }

  const tokens = await loginRes.json();
  const cookieStore = await cookies();
  setAuthCookies(cookieStore, tokens);

  return NextResponse.json({ registered: true, autoLogin: true });
}
```

**Register 자동 로그인 실패 시 클라이언트 처리:**

BFF Register 라우트가 `{ registered: true, autoLogin: false }` (status 201)을 반환하면, 클라이언트에서 로그인 페이지로 안내합니다:

```typescript
// 회원가입 mutation onSuccess 핸들러
const res = await fetch("/api/auth/register", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(data),
});
const result = await res.json();

if (result.autoLogin === false) {
  // 회원가입 성공, 자동 로그인 실패 → 로그인 페이지로 안내
  toast.success("회원가입이 완료되었습니다. 로그인해주세요.");
  router.push("/login");
  return;
}

// 자동 로그인 성공 → 대시보드로 이동
router.push("/dashboard");
router.refresh();
```

**Login 후 사용자 정보 획득 흐름:**

1. `POST /api/auth/login` (BFF) 성공 → 쿠키 설정 완료
2. 로그인 성공 콜백에서 `queryClient.invalidateQueries({ queryKey: userKeys.me() })` 호출
3. TanStack Query가 `GET /api/users/me` → BFF → Backend 요청
4. Backend가 JWT에서 user_id 추출 → User 조회 → UserResponse 반환

### 1.4 Query Key Factory

```typescript
// hooks/queries/keys.ts
export const userKeys = {
  all: ["users"] as const,
  me: () => [...userKeys.all, "me"] as const,
  lists: () => [...userKeys.all, "list"] as const,
  list: (params: UserListParams) => [...userKeys.lists(), params] as const,
  details: () => [...userKeys.all, "detail"] as const,
  detail: (id: string) => [...userKeys.details(), id] as const,
};
```

```typescript
// hooks/queries/use-current-user.ts
import { useQuery } from "@tanstack/react-query";
import { getMe } from "@/client/sdk.gen";
import { userKeys } from "./keys";

export function useCurrentUser() {
  return useQuery({
    queryKey: userKeys.me(),
    queryFn: () => getMe(),
    staleTime: 5 * 60 * 1000,
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

### 1.12 로그인 폼 / Auth Hooks

Auth 요청은 BFF 전용 라우트(`/api/auth/*`)를 직접 fetch로 호출합니다. openapi-ts SDK는 사용하지 않습니다.

```typescript
// src/components/features/auth/login-form.tsx
"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useRouter, useSearchParams } from "next/navigation";
import { toast } from "sonner";
import { useLogin } from "@/hooks/queries/use-auth";
import { ApiError } from "@/lib/api-error";

const loginSchema = z.object({
  email: z.string().email("올바른 이메일을 입력하세요"),
  password: z.string().min(1, "비밀번호를 입력하세요"),
});

type LoginFormValues = z.infer<typeof loginSchema>;

export function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const callbackUrl = searchParams.get("callbackUrl") ?? "/dashboard";
  const loginMutation = useLogin();

  const form = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "" },
  });

  async function onSubmit(data: LoginFormValues) {
    try {
      await loginMutation.mutateAsync(data);
      router.push(callbackUrl);
      router.refresh();
    } catch (error) {
      if (error instanceof ApiError) {
        if (error.isValidationError) {
          Object.entries(error.fieldErrors).forEach(([field, message]) => {
            form.setError(field as keyof LoginFormValues, { message });
          });
        } else {
          toast.error(error.message);
        }
      } else {
        toast.error("로그인 중 오류가 발생했습니다.");
      }
    }
  }

  return (
    <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
      {/* 실제 UI는 shadcn/ui Form 컴포넌트 사용 권장 */}
      <div>{/* email input */}</div>
      <div>{/* password input */}</div>
      <button type="submit" disabled={loginMutation.isPending}>
        {loginMutation.isPending ? "로그인 중..." : "로그인"}
      </button>
    </form>
  );
}
```

**useLogin / useLogout mutation hooks:**

```typescript
// hooks/queries/use-auth.ts
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ApiError } from "@/lib/api-error";
import { userKeys } from "./keys";

export function useLogin() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: { email: string; password: string }) => {
      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });
      if (!res.ok) {
        const body = await res.json();
        throw new ApiError(res.status, body.error);
      }
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: userKeys.me() });
    },
  });
}

export function useLogout() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      await fetch("/api/auth/logout", { method: "POST" });
    },
    onSuccess: () => {
      queryClient.clear();
      window.location.replace("/login");
    },
  });
}
```

**Auth 요청 규칙:**
- 로그인, 회원가입, 토큰 갱신, 로그아웃은 **BFF 전용 라우트**(`/api/auth/*`)를 `fetch()`로 직접 호출합니다
- openapi-ts SDK가 생성하는 auth 함수(`login()`, `refresh()` 등)는 **사용하지 않습니다**
  - SDK의 auth 함수는 BFF를 우회하므로 쿠키가 설정되지 않습니다
- openapi-ts SDK는 **인증된 일반 API 요청**(users, posts 등)에만 사용합니다

### 1.13 테스트 설정 + 컴포넌트/훅 테스트

#### 테스트 설정

```typescript
// src/tests/setup.ts
import "@testing-library/jest-dom/vitest";
```

#### 컴포넌트 테스트 예시

```typescript
// src/components/features/auth/__tests__/login-form.test.tsx
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "@/tests/utils";
import { LoginForm } from "../login-form";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";

const server = setupServer();
beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe("LoginForm", () => {
  it("should display error message when login fails", async () => {
    server.use(
      http.post("/api/auth/login", () =>
        HttpResponse.json(
          { error: { code: "UNAUTHORIZED", message: "Invalid email or password", details: null } },
          { status: 401 },
        ),
      ),
    );
    renderWithProviders(<LoginForm />);
    // ... test interaction
  });
});
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
