import { NextRequest } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { cookiesMock, setAuthCookiesMock } = vi.hoisted(() => ({
  cookiesMock: vi.fn(),
  setAuthCookiesMock: vi.fn()
}));

const fetchMock = vi.fn<typeof fetch>();

vi.mock("next/headers", () => ({
  cookies: cookiesMock
}));

vi.mock("@/lib/auth-cookies", () => ({
  setAuthCookies: setAuthCookiesMock
}));

import { POST } from "@/app/api/auth/test-login/route";

interface CookieStore {
  set: ReturnType<typeof vi.fn>;
}

function createRequest(body: { email: string; name?: string }): NextRequest {
  return new NextRequest("http://localhost:3000/api/auth/test-login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });
}

describe("POST /api/auth/test-login", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    fetchMock.mockReset();
    vi.stubGlobal("fetch", fetchMock);
    process.env.BACKEND_URL = "http://localhost:8000";
    delete process.env.AUTH_TEST_MODE;
    delete process.env.AUTH_TEST_SECRET;
  });

  it("should return 404 when test mode is disabled", async () => {
    const response = await POST(
      createRequest({ email: "e2e-user@example.com", name: "E2E User" })
    );

    expect(response.status).toBe(404);
    await expect(response.json()).resolves.toEqual({
      error: {
        code: "NOT_FOUND",
        message: "Not found",
        details: null
      }
    });
    expect(fetchMock).not.toHaveBeenCalled();
    expect(setAuthCookiesMock).not.toHaveBeenCalled();
  });

  it("should forward to backend, set cookies, and return 204", async () => {
    process.env.AUTH_TEST_MODE = "true";
    process.env.AUTH_TEST_SECRET = "test-auth-secret";

    const cookieStore: CookieStore = {
      set: vi.fn()
    };
    cookiesMock.mockResolvedValue(cookieStore);

    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          access_token: "new-access-token",
          refresh_token: "new-refresh-token",
          token_type: "bearer"
        }),
        {
          status: 200,
          headers: { "Content-Type": "application/json" }
        }
      )
    );

    const response = await POST(
      createRequest({ email: "e2e-user@example.com", name: "E2E User" })
    );

    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/auth/test-login",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "x-test-auth-secret": "test-auth-secret"
        },
        body: JSON.stringify({ email: "e2e-user@example.com", name: "E2E User" })
      }
    );
    expect(setAuthCookiesMock).toHaveBeenCalledWith(cookieStore, {
      access_token: "new-access-token",
      refresh_token: "new-refresh-token"
    });
    expect(response.status).toBe(204);
  });

  it("should pass through backend unauthorized response", async () => {
    process.env.AUTH_TEST_MODE = "true";
    process.env.AUTH_TEST_SECRET = "wrong-secret";

    cookiesMock.mockResolvedValue({ set: vi.fn() });

    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          error: {
            code: "UNAUTHORIZED",
            message: "Invalid test auth secret",
            details: null
          }
        }),
        {
          status: 401,
          headers: { "Content-Type": "application/json" }
        }
      )
    );

    const response = await POST(
      createRequest({ email: "e2e-user@example.com" })
    );

    expect(response.status).toBe(401);
    await expect(response.json()).resolves.toEqual({
      error: {
        code: "UNAUTHORIZED",
        message: "Invalid test auth secret",
        details: null
      }
    });
    expect(setAuthCookiesMock).not.toHaveBeenCalled();
  });
});
