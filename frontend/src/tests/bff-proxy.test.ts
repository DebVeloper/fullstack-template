import { NextRequest } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { cookiesMock } = vi.hoisted(() => ({
  cookiesMock: vi.fn()
}));

const fetchMock = vi.fn<typeof fetch>();

vi.mock("next/headers", () => ({
  cookies: cookiesMock
}));

interface CookieStore {
  get: (name: string) => { value: string } | undefined;
  set: ReturnType<typeof vi.fn>;
}

type NextRequestInit = ConstructorParameters<typeof NextRequest>[1];

function createCookieStore(accessToken?: string): CookieStore {
  return {
    get: (name: string) => {
      if (name === "access_token" && accessToken) {
        return { value: accessToken };
      }

      return undefined;
    },
    set: vi.fn()
  };
}

function createRequest(path: string, init?: NextRequestInit): NextRequest {
  return new NextRequest(`http://localhost:3000${path}`, init);
}

async function importProxyRoute() {
  vi.resetModules();
  return import("@/app/api/[...path]/route");
}

describe("BFF proxy", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    fetchMock.mockReset();
    vi.stubGlobal("fetch", fetchMock);
    process.env.BACKEND_URL = "http://localhost:8000";
  });

  it("should proxy request path/query and forward Authorization header from access cookie", async () => {
    cookiesMock.mockResolvedValue(createCookieStore("access-token"));

    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: {
          "Content-Type": "application/json",
          Connection: "keep-alive",
          "X-Trace-Id": "trace-1"
        }
      })
    );

    const { GET } = await importProxyRoute();
    const response = await GET(createRequest("/api/v1/users/me?page=1"));

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://localhost:8000/api/v1/users/me?page=1");
    expect((init.headers as Headers).get("authorization")).toBe("Bearer access-token");

    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toEqual({ ok: true });
    expect(response.headers.get("x-trace-id")).toBe("trace-1");
    expect(response.headers.get("connection")).toBeNull();
  });

  it("should return 502 with unified error envelope when backend is unavailable", async () => {
    cookiesMock.mockResolvedValue(createCookieStore());
    fetchMock.mockRejectedValueOnce(new Error("network down"));

    const { GET } = await importProxyRoute();
    const response = await GET(createRequest("/api/v1/users/me"));

    expect(response.status).toBe(502);
    await expect(response.json()).resolves.toEqual({
      error: {
        code: "BAD_GATEWAY",
        message: "Backend service unavailable",
        details: null
      }
    });
  });

  it("should forward request body for non-GET methods", async () => {
    cookiesMock.mockResolvedValue(createCookieStore());

    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ created: true }), {
        status: 201,
        headers: { "Content-Type": "application/json" }
      })
    );

    const { POST } = await importProxyRoute();
    const response = await POST(
      createRequest("/api/v1/admin/users", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: "user@example.com" })
      })
    );

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(init.body).toBeInstanceOf(ArrayBuffer);
    expect(response.status).toBe(201);
    await expect(response.json()).resolves.toEqual({ created: true });
  });
});
