# Frontend Reference Specifications

> 이 문서는 Frontend에서 사용하는 **참조 구현 코드(보일러플레이트)**를 모아둔 것입니다.
> 규칙과 컨벤션은 [CONVENTIONS-FRONTEND.md](./CONVENTIONS-FRONTEND.md)를 참조하세요.

---

## 1. Core

### 1.1 BFF 프록시

BFF 프록시는 Backend에서 401 응답을 받으면 자동으로 토큰 갱신을 시도합니다 (Silent Refresh). 갱신 성공 시 새 쿠키를 설정하고 원래 요청을 재시도합니다. 갱신 실패 시 쿠키를 삭제하고 401을 클라이언트에 전달합니다.

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
        const refreshResponse = await fetch(
          `${BACKEND_URL}/api/v1/auth/refresh`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ refresh_token: refreshToken }),
          },
        );

        if (refreshResponse.ok) {
          const tokens = await refreshResponse.json();

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

          // 새 access_token으로 원래 요청 재시도
          headers.set("Authorization", `Bearer ${tokens.access_token}`);
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

const AUTH_ROUTES = ["/dashboard", "/settings"];
const PUBLIC_ONLY_ROUTES = ["/login", "/register"];

export function middleware(req: NextRequest) {
  const accessToken = req.cookies.get("access_token")?.value;
  const { pathname } = req.nextUrl;

  // 인증 필요 라우트에 미인증 접근 → /login 리다이렉트
  const isAuthRoute = AUTH_ROUTES.some((route) => pathname.startsWith(route));
  if (isAuthRoute && !accessToken) {
    const loginUrl = new URL("/login", req.url);
    loginUrl.searchParams.set("callbackUrl", pathname);
    return NextResponse.redirect(loginUrl);
  }

  // 로그인된 사용자가 공개 전용 라우트 접근 → /dashboard 리다이렉트
  const isPublicOnly = PUBLIC_ONLY_ROUTES.some((route) => pathname.startsWith(route));
  if (isPublicOnly && accessToken) {
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
  throwOnError: true, // 4xx/5xx 응답 시 에러 throw
});

// SDK 에러 → ApiError 변환 인터셉터
apiClient.interceptors.response.use((response) => {
  if (response.status >= 400) {
    const body = response.data as { error?: { code: string; message: string; details: unknown } };
    if (body?.error) {
      throw new ApiError(response.status, body.error);
    }
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
              window.location.href = "/login";
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
