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
    return NextResponse.redirect(new URL(DEFAULT_AUTHENTICATED_REDIRECT_PATH, request.url));
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
