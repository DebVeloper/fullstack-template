import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";

import { clearAuthCookies, setAuthCookies } from "@/lib/auth-cookies";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

const HOP_BY_HOP_HEADERS = new Set([
  "connection",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailers",
  "transfer-encoding",
  "upgrade"
]);

interface BackendTokenResponse {
  access_token: string;
  refresh_token: string;
}

interface RefreshSuccessResult {
  success: true;
  tokens: BackendTokenResponse;
}

interface RefreshFailureResult {
  success: false;
}

type RefreshResult = RefreshSuccessResult | RefreshFailureResult;

let refreshPromise: Promise<RefreshResult> | null = null;

function filterResponseHeaders(headers: Headers): Headers {
  const filtered = new Headers();

  headers.forEach((value, key) => {
    if (!HOP_BY_HOP_HEADERS.has(key.toLowerCase())) {
      filtered.set(key, value);
    }
  });

  return filtered;
}

function createBackendRequestHeaders(request: NextRequest, accessToken?: string): Headers {
  const headers = new Headers(request.headers);

  headers.delete("host");
  headers.delete("cookie");

  HOP_BY_HOP_HEADERS.forEach((headerName) => {
    headers.delete(headerName);
  });

  if (accessToken) {
    headers.set("Authorization", `Bearer ${accessToken}`);
  }

  return headers;
}

function createBackendUrl(request: NextRequest): string {
  const path = request.nextUrl.pathname.replace(/^\/api\//, "");
  return `${BACKEND_URL}/api/${path}${request.nextUrl.search}`;
}

function createBadGatewayResponse(): NextResponse {
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

function createUnauthorizedResponse(): NextResponse {
  return NextResponse.json(
    {
      error: {
        code: "UNAUTHORIZED",
        message: "Authentication required",
        details: null
      }
    },
    { status: 401 }
  );
}

function proxyResponse(response: Response): NextResponse {
  return new NextResponse(response.body, {
    status: response.status,
    headers: filterResponseHeaders(response.headers)
  });
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
        body: JSON.stringify({ refresh_token: currentRefreshToken })
      });

      if (!response.ok) {
        return { success: false };
      }

      const tokens = (await response.json()) as BackendTokenResponse;

      if (!tokens.access_token || !tokens.refresh_token) {
        return { success: false };
      }

      return {
        success: true,
        tokens
      };
    } catch {
      return { success: false };
    } finally {
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}

async function proxyRequest(request: NextRequest): Promise<NextResponse> {
  const backendUrl = createBackendUrl(request);
  const cookieStore = await cookies();
  const accessToken = cookieStore.get("access_token")?.value;
  const headers = createBackendRequestHeaders(request, accessToken);

  let bodyBuffer: ArrayBuffer | null = null;
  if (request.method !== "GET" && request.method !== "HEAD") {
    bodyBuffer = await request.arrayBuffer();
  }

  const backendRequestInit: RequestInit = {
    method: request.method,
    headers
  };

  if (bodyBuffer) {
    backendRequestInit.body = bodyBuffer;
  }

  let response: Response;
  try {
    response = await fetch(backendUrl, backendRequestInit);
  } catch {
    return createBadGatewayResponse();
  }

  if (response.status !== 401) {
    return proxyResponse(response);
  }

  const refreshToken = cookieStore.get("refresh_token")?.value;

  if (!refreshToken) {
    return proxyResponse(response);
  }

  const refreshResult = await refreshTokens(refreshToken);

  if (!refreshResult.success) {
    clearAuthCookies(cookieStore);
    return createUnauthorizedResponse();
  }

  setAuthCookies(cookieStore, refreshResult.tokens);

  headers.set("Authorization", `Bearer ${refreshResult.tokens.access_token}`);

  try {
    response = await fetch(backendUrl, backendRequestInit);
  } catch {
    return createBadGatewayResponse();
  }

  if (response.status === 401) {
    clearAuthCookies(cookieStore);
  }

  return proxyResponse(response);
}

export const GET = proxyRequest;
export const POST = proxyRequest;
export const PUT = proxyRequest;
export const PATCH = proxyRequest;
export const DELETE = proxyRequest;
