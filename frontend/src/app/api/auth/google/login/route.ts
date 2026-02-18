import { createHash, randomBytes } from "node:crypto";

import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";

const GOOGLE_AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth";
const GOOGLE_OAUTH_SCOPE = "openid email profile";
const DEFAULT_CALLBACK_URL = "/dashboard";
const OAUTH_COOKIE_MAX_AGE_SECONDS = 60 * 10;
const IS_PRODUCTION = process.env.NODE_ENV === "production";

const GOOGLE_OAUTH_CLIENT_ID = process.env.GOOGLE_OAUTH_CLIENT_ID ?? "";
const GOOGLE_OAUTH_REDIRECT_URI =
  process.env.GOOGLE_OAUTH_REDIRECT_URI ?? "http://localhost:3000/api/auth/google/callback";

function toBase64Url(value: Buffer): string {
  return value
    .toString("base64")
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/u, "");
}

function generateCodeVerifier(): string {
  return toBase64Url(randomBytes(32));
}

function generateCodeChallenge(codeVerifier: string): string {
  return toBase64Url(createHash("sha256").update(codeVerifier).digest());
}

function generateState(): string {
  return toBase64Url(randomBytes(16));
}

function sanitizeCallbackUrl(callbackUrl: string | null): string {
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

export async function GET(request: NextRequest): Promise<NextResponse> {
  if (!GOOGLE_OAUTH_CLIENT_ID) {
    return NextResponse.json(
      {
        error: {
          code: "CONFIGURATION_ERROR",
          message: "Missing GOOGLE_OAUTH_CLIENT_ID",
          details: null
        }
      },
      { status: 500 }
    );
  }

  const codeVerifier = generateCodeVerifier();
  const codeChallenge = generateCodeChallenge(codeVerifier);
  const state = generateState();
  const callbackUrl = sanitizeCallbackUrl(request.nextUrl.searchParams.get("callbackUrl"));

  const cookieStore = await cookies();

  cookieStore.set("google_oauth_state", state, {
    httpOnly: true,
    secure: IS_PRODUCTION,
    sameSite: "lax",
    path: "/",
    maxAge: OAUTH_COOKIE_MAX_AGE_SECONDS
  });

  cookieStore.set("google_oauth_code_verifier", codeVerifier, {
    httpOnly: true,
    secure: IS_PRODUCTION,
    sameSite: "lax",
    path: "/",
    maxAge: OAUTH_COOKIE_MAX_AGE_SECONDS
  });

  cookieStore.set("google_oauth_callback_url", callbackUrl, {
    httpOnly: true,
    secure: IS_PRODUCTION,
    sameSite: "lax",
    path: "/",
    maxAge: OAUTH_COOKIE_MAX_AGE_SECONDS
  });

  const authorizeUrl = new URL(GOOGLE_AUTHORIZE_URL);
  authorizeUrl.searchParams.set("client_id", GOOGLE_OAUTH_CLIENT_ID);
  authorizeUrl.searchParams.set("redirect_uri", GOOGLE_OAUTH_REDIRECT_URI);
  authorizeUrl.searchParams.set("response_type", "code");
  authorizeUrl.searchParams.set("scope", GOOGLE_OAUTH_SCOPE);
  authorizeUrl.searchParams.set("state", state);
  authorizeUrl.searchParams.set("code_challenge", codeChallenge);
  authorizeUrl.searchParams.set("code_challenge_method", "S256");
  authorizeUrl.searchParams.set("access_type", "offline");

  return NextResponse.redirect(authorizeUrl);
}
