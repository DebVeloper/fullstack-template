import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";

import { setAuthCookies } from "@/lib/auth-cookies";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";
const DEFAULT_CALLBACK_URL = "/dashboard";
const IS_PRODUCTION = process.env.NODE_ENV === "production";

const OAUTH_STATE_COOKIE_NAME = "google_oauth_state";
const OAUTH_CODE_VERIFIER_COOKIE_NAME = "google_oauth_code_verifier";
const OAUTH_CALLBACK_URL_COOKIE_NAME = "google_oauth_callback_url";

type CookieStore = Pick<Awaited<ReturnType<typeof cookies>>, "get" | "set">;

interface BackendTokenResponse {
  access_token: string;
  refresh_token: string;
}

function sanitizeCallbackUrl(callbackUrl: string | undefined): string {
  if (!callbackUrl) {
    return DEFAULT_CALLBACK_URL;
  }

  const normalized = callbackUrl.trim();

  if (!normalized) {
    return DEFAULT_CALLBACK_URL;
  }

  try {
    const parsedUrl = new URL(normalized, "http://localhost");

    if (parsedUrl.origin !== "http://localhost") {
      return DEFAULT_CALLBACK_URL;
    }

    if (!parsedUrl.pathname.startsWith("/")) {
      return DEFAULT_CALLBACK_URL;
    }

    return `${parsedUrl.pathname}${parsedUrl.search}${parsedUrl.hash}`;
  } catch {
    return DEFAULT_CALLBACK_URL;
  }
}

function clearOAuthCookies(cookieStore: CookieStore): void {
  const clearCookieOptions = {
    httpOnly: true,
    secure: IS_PRODUCTION,
    sameSite: "lax" as const,
    path: "/",
    maxAge: 0
  };

  cookieStore.set(OAUTH_STATE_COOKIE_NAME, "", clearCookieOptions);
  cookieStore.set(OAUTH_CODE_VERIFIER_COOKIE_NAME, "", clearCookieOptions);
  cookieStore.set(OAUTH_CALLBACK_URL_COOKIE_NAME, "", clearCookieOptions);
}

function createOAuthErrorResponse(status: number, code: string, message: string): NextResponse {
  return NextResponse.json(
    {
      error: {
        code,
        message,
        details: null
      }
    },
    { status }
  );
}

export async function GET(request: NextRequest): Promise<NextResponse> {
  const cookieStore = await cookies();
  const code = request.nextUrl.searchParams.get("code");
  const state = request.nextUrl.searchParams.get("state");
  const expectedState = cookieStore.get(OAUTH_STATE_COOKIE_NAME)?.value;
  const codeVerifier = cookieStore.get(OAUTH_CODE_VERIFIER_COOKIE_NAME)?.value;
  const callbackUrl = cookieStore.get(OAUTH_CALLBACK_URL_COOKIE_NAME)?.value;

  if (!code || !state) {
    clearOAuthCookies(cookieStore);
    return createOAuthErrorResponse(400, "BAD_REQUEST", "Missing OAuth callback parameters");
  }

  if (!expectedState || !codeVerifier) {
    clearOAuthCookies(cookieStore);
    return createOAuthErrorResponse(401, "UNAUTHORIZED", "Missing OAuth state or verifier");
  }

  if (state !== expectedState) {
    clearOAuthCookies(cookieStore);
    return createOAuthErrorResponse(401, "UNAUTHORIZED", "Invalid OAuth state");
  }

  let exchangeResponse: Response;

  try {
    exchangeResponse = await fetch(`${BACKEND_URL}/api/v1/auth/google/exchange`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        code,
        code_verifier: codeVerifier
      })
    });
  } catch {
    clearOAuthCookies(cookieStore);
    return createOAuthErrorResponse(502, "BAD_GATEWAY", "Backend service unavailable");
  }

  if (!exchangeResponse.ok) {
    clearOAuthCookies(cookieStore);

    try {
      const errorPayload = (await exchangeResponse.json()) as unknown;
      return NextResponse.json(errorPayload, { status: exchangeResponse.status });
    } catch {
      return createOAuthErrorResponse(exchangeResponse.status, "OAUTH_EXCHANGE_FAILED", "OAuth exchange failed");
    }
  }

  const tokenResponse = (await exchangeResponse.json()) as Partial<BackendTokenResponse>;

  if (!tokenResponse.access_token || !tokenResponse.refresh_token) {
    clearOAuthCookies(cookieStore);
    return createOAuthErrorResponse(502, "BAD_GATEWAY", "Invalid token response from backend");
  }

  setAuthCookies(cookieStore, {
    access_token: tokenResponse.access_token,
    refresh_token: tokenResponse.refresh_token
  });

  clearOAuthCookies(cookieStore);

  const redirectPath = sanitizeCallbackUrl(callbackUrl);
  return NextResponse.redirect(new URL(redirectPath, request.url));
}
