import { NextRequest } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { cookiesMock, setAuthCookiesMock, clearAuthCookiesMock } = vi.hoisted(() => ({
  cookiesMock: vi.fn(),
  setAuthCookiesMock: vi.fn(),
  clearAuthCookiesMock: vi.fn()
}));

const fetchMock = vi.fn<typeof fetch>();

vi.mock("next/headers", () => ({
  cookies: cookiesMock
}));

vi.mock("@/lib/auth-cookies", () => ({
  setAuthCookies: setAuthCookiesMock,
  clearAuthCookies: clearAuthCookiesMock
}));

interface CookieStore {
  get: (name: string) => { value: string } | undefined;
  set: ReturnType<typeof vi.fn>;
}

function createCookieStore({
  accessToken,
  refreshToken,
  requestPath
}: {
  accessToken?: string;
  refreshToken?: string;
  requestPath: string;
}): CookieStore {
  return {
    get: (name: string) => {
      if (name === "access_token" && accessToken) {
        return { value: accessToken };
      }

      if (name === "refresh_token" && refreshToken && requestPath.startsWith("/api")) {
        return { value: refreshToken };
      }

      return undefined;
    },
    set: vi.fn()
  };
}

function createRequest(path: string): NextRequest {
  return new NextRequest(`http://localhost:3000${path}`);
}

async function importProxyRoute() {
  vi.resetModules();
  return import("@/app/api/[...path]/route");
}

describe("BFF proxy silent refresh", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    fetchMock.mockReset();
    vi.stubGlobal("fetch", fetchMock);
    process.env.BACKEND_URL = "http://localhost:8000";
  });

  it("should refresh on 401, set auth cookies, and retry once with new token", async () => {
    const path = "/api/v1/users/me";
    const cookieStore = createCookieStore({
      accessToken: "expired-access-token",
      refreshToken: "refresh-token-from-api-cookie",
      requestPath: path
    });
    cookiesMock.mockResolvedValue(cookieStore);

    fetchMock.mockImplementation(async (input, init) => {
      const url = String(input);
      const headers = init?.headers as Headers;

      if (url === "http://localhost:8000/api/v1/auth/refresh") {
        expect(init?.method).toBe("POST");
        expect(init?.body).toBe(JSON.stringify({ refresh_token: "refresh-token-from-api-cookie" }));

        return new Response(
          JSON.stringify({
            access_token: "new-access-token",
            refresh_token: "new-refresh-token"
          }),
          {
            status: 200,
            headers: { "Content-Type": "application/json" }
          }
        );
      }

      if (url === "http://localhost:8000/api/v1/users/me") {
        const authorization = headers.get("authorization");

        if (authorization === "Bearer expired-access-token") {
          return new Response(JSON.stringify({ error: { code: "UNAUTHORIZED" } }), {
            status: 401,
            headers: { "Content-Type": "application/json" }
          });
        }

        expect(authorization).toBe("Bearer new-access-token");
        return new Response(JSON.stringify({ id: "u-1" }), {
          status: 200,
          headers: { "Content-Type": "application/json" }
        });
      }

      throw new Error(`Unexpected URL ${url}`);
    });

    const { GET } = await importProxyRoute();
    const response = await GET(createRequest(path));

    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(setAuthCookiesMock).toHaveBeenCalledWith(cookieStore, {
      access_token: "new-access-token",
      refresh_token: "new-refresh-token"
    });
    expect(clearAuthCookiesMock).not.toHaveBeenCalled();
    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toEqual({ id: "u-1" });
  });

  it("should clear auth cookies and return 401 when refresh fails", async () => {
    const path = "/api/v1/users/me";
    const cookieStore = createCookieStore({
      accessToken: "expired-access-token",
      refreshToken: "refresh-token-from-api-cookie",
      requestPath: path
    });
    cookiesMock.mockResolvedValue(cookieStore);

    fetchMock.mockImplementation(async (input) => {
      const url = String(input);

      if (url === "http://localhost:8000/api/v1/users/me") {
        return new Response(JSON.stringify({ error: { code: "UNAUTHORIZED" } }), {
          status: 401,
          headers: { "Content-Type": "application/json" }
        });
      }

      if (url === "http://localhost:8000/api/v1/auth/refresh") {
        return new Response(JSON.stringify({ error: { code: "UNAUTHORIZED" } }), {
          status: 401,
          headers: { "Content-Type": "application/json" }
        });
      }

      throw new Error(`Unexpected URL ${url}`);
    });

    const { GET } = await importProxyRoute();
    const response = await GET(createRequest(path));

    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(clearAuthCookiesMock).toHaveBeenCalledWith(cookieStore);
    expect(setAuthCookiesMock).not.toHaveBeenCalled();
    expect(response.status).toBe(401);
  });

  it("should share one refresh call across concurrent 401 responses", async () => {
    const path = "/api/v1/users/me";
    const cookieStore = createCookieStore({
      accessToken: "expired-access-token",
      refreshToken: "refresh-token-from-api-cookie",
      requestPath: path
    });
    cookiesMock.mockResolvedValue(cookieStore);

    let refreshCalls = 0;

    fetchMock.mockImplementation(async (input, init) => {
      const url = String(input);
      const headers = init?.headers as Headers;

      if (url === "http://localhost:8000/api/v1/auth/refresh") {
        refreshCalls += 1;
        await new Promise((resolve) => {
          setTimeout(resolve, 10);
        });

        return new Response(
          JSON.stringify({
            access_token: "shared-new-access-token",
            refresh_token: "shared-new-refresh-token"
          }),
          {
            status: 200,
            headers: { "Content-Type": "application/json" }
          }
        );
      }

      if (url === "http://localhost:8000/api/v1/users/me") {
        const authorization = headers.get("authorization");

        if (authorization === "Bearer expired-access-token") {
          return new Response(JSON.stringify({ error: { code: "UNAUTHORIZED" } }), {
            status: 401,
            headers: { "Content-Type": "application/json" }
          });
        }

        return new Response(JSON.stringify({ ok: true }), {
          status: 200,
          headers: { "Content-Type": "application/json" }
        });
      }

      throw new Error(`Unexpected URL ${url}`);
    });

    const { GET } = await importProxyRoute();
    const [responseA, responseB] = await Promise.all([
      GET(createRequest(path)),
      GET(createRequest(path))
    ]);

    expect(refreshCalls).toBe(1);
    expect(responseA.status).toBe(200);
    expect(responseB.status).toBe(200);
  });
});
