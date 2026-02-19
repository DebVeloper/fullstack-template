import type { NextRequest } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { cookiesMock, setAuthCookiesMock, clearAuthCookiesMock } = vi.hoisted(() => ({
  cookiesMock: vi.fn(),
  setAuthCookiesMock: vi.fn(),
  clearAuthCookiesMock: vi.fn()
}));

const fetchMock = vi.fn();

vi.mock("next/headers", () => ({
  cookies: cookiesMock
}));

vi.mock("@/lib/auth-cookies", () => ({
  setAuthCookies: setAuthCookiesMock,
  clearAuthCookies: clearAuthCookiesMock
}));

import { POST } from "@/app/api/auth/refresh/route";

describe("POST /api/auth/refresh", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    process.env.BACKEND_URL = "http://localhost:8000";
    fetchMock.mockReset();
    vi.stubGlobal("fetch", fetchMock);
  });

  it("should return 401 and clear cookies when refresh token cookie is missing", async () => {
    const cookieStore = {
      get: vi.fn().mockReturnValue(undefined)
    };
    cookiesMock.mockResolvedValue(cookieStore);

    const response = await POST({} as NextRequest);

    expect(response.status).toBe(401);
    await expect(response.json()).resolves.toEqual({
      error: {
        code: "UNAUTHORIZED",
        message: "No refresh token",
        details: null
      }
    });
    expect(clearAuthCookiesMock).toHaveBeenCalledWith(cookieStore);
    expect(fetch).not.toHaveBeenCalled();
  });

  it("should refresh tokens, set cookies, and return 200", async () => {
    const cookieStore = {
      get: vi.fn().mockReturnValue({ value: "refresh-token" })
    };
    cookiesMock.mockResolvedValue(cookieStore);

    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          access_token: "new-access-token",
          refresh_token: "new-refresh-token"
        }),
        {
          status: 200,
          headers: { "Content-Type": "application/json" }
        }
      )
    );

    const response = await POST({} as NextRequest);

    expect(fetch).toHaveBeenCalledWith("http://localhost:8000/api/v1/auth/refresh", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: "refresh-token" })
    });
    expect(setAuthCookiesMock).toHaveBeenCalledWith(cookieStore, {
      access_token: "new-access-token",
      refresh_token: "new-refresh-token"
    });
    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toEqual({ token_type: "bearer" });
  });
});
