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
