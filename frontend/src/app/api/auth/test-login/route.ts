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
