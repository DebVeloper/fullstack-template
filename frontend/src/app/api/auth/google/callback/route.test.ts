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

import { GET } from "@/app/api/auth/google/callback/route";

interface MockCookieStore {
  get: (name: string) => { value: string } | undefined;
  set: ReturnType<typeof vi.fn>;
}

function createCookieStore(values: Record<string, string | undefined>): MockCookieStore {
  return {
    get: (name: string) => {
      const value = values[name];
      if (!value) {
        return undefined;
      }

      return { value };
    },
    set: vi.fn()
  };
}

function createRequest(path: string): NextRequest {
  return new NextRequest(`http://localhost:3000${path}`);
}

describe("GET /api/auth/google/callback", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    fetchMock.mockReset();
    vi.stubGlobal("fetch", fetchMock);
  });

  it("should reject mismatched state and not set auth cookies", async () => {
    const cookieStore = createCookieStore({
      google_oauth_state: "expected-state",
      google_oauth_code_verifier: "pkce-verifier",
      google_oauth_callback_url: "/dashboard"
    });
    cookiesMock.mockResolvedValue(cookieStore);

    const response = await GET(
      createRequest("/api/auth/google/callback?code=oauth-code&state=invalid-state")
    );

    expect(response.status).toBe(401);
    await expect(response.json()).resolves.toEqual({
      error: {
        code: "UNAUTHORIZED",
        message: "Invalid OAuth state",
        details: null
      }
    });

    expect(fetchMock).not.toHaveBeenCalled();
    expect(setAuthCookiesMock).not.toHaveBeenCalled();
    expect(cookieStore.set).toHaveBeenCalledTimes(3);
  });

  it("should return backend error and not set auth cookies when exchange fails", async () => {
    const cookieStore = createCookieStore({
      google_oauth_state: "expected-state",
      google_oauth_code_verifier: "pkce-verifier",
      google_oauth_callback_url: "/dashboard"
    });
    cookiesMock.mockResolvedValue(cookieStore);

    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          error: {
            code: "UNAUTHORIZED",
            message: "OAuth exchange failed",
            details: null
          }
        }),
        {
          status: 401,
          headers: { "Content-Type": "application/json" }
        }
      )
    );

    const response = await GET(
      createRequest("/api/auth/google/callback?code=oauth-code&state=expected-state")
    );

    expect(fetchMock).toHaveBeenCalledWith("http://localhost:8000/api/v1/auth/google/exchange", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        code: "oauth-code",
        code_verifier: "pkce-verifier"
      })
    });
    expect(response.status).toBe(401);
    await expect(response.json()).resolves.toEqual({
      error: {
        code: "UNAUTHORIZED",
        message: "OAuth exchange failed",
        details: null
      }
    });
    expect(setAuthCookiesMock).not.toHaveBeenCalled();
    expect(cookieStore.set).toHaveBeenCalledTimes(3);
  });

  it("should sanitize external callback URL and redirect to dashboard", async () => {
    const cookieStore = createCookieStore({
      google_oauth_state: "expected-state",
      google_oauth_code_verifier: "pkce-verifier",
      google_oauth_callback_url: "https://evil.com"
    });
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

    const response = await GET(
      createRequest("/api/auth/google/callback?code=oauth-code&state=expected-state")
    );

    expect(setAuthCookiesMock).toHaveBeenCalledWith(cookieStore, {
      access_token: "new-access-token",
      refresh_token: "new-refresh-token"
    });
    expect(cookieStore.set).toHaveBeenCalledTimes(3);
    expect(response.status).toBe(307);
    expect(response.headers.get("location")).toBe("http://localhost:3000/dashboard");
  });
});
