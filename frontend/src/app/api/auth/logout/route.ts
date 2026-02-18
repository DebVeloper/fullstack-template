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
      body: JSON.stringify({ refresh_token: refreshToken })
    }).catch(() => undefined);
  }

  clearAuthCookies(cookieStore);
  return new NextResponse(null, { status: 204 });
}
