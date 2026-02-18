import { NextRequest } from "next/server";
import { describe, expect, it } from "vitest";

import { middleware } from "@/middleware";

function createRequest(path: string, accessToken?: string): NextRequest {
  const headers = new Headers();

  if (accessToken) {
    headers.set("cookie", `access_token=${accessToken}`);
  }

  return new NextRequest(`http://localhost:3000${path}`, { headers });
}

describe("middleware", () => {
  it("should redirect unauthenticated users to login with relative callbackUrl", () => {
    const response = middleware(createRequest("/dashboard?tab=users"));

    expect(response.status).toBe(307);
    expect(response.headers.get("location")).toBe(
      "http://localhost:3000/login?callbackUrl=%2Fdashboard%3Ftab%3Dusers"
    );
  });

  it("should never redirect authenticated login requests to external callbackUrl", () => {
    const response = middleware(createRequest("/login?callbackUrl=https://evil.com", "access-token"));

    expect(response.status).toBe(307);
    expect(response.headers.get("location")).toBe("http://localhost:3000/dashboard");
  });

  it("should allow unauthenticated access to login page", () => {
    const response = middleware(createRequest("/login?callbackUrl=%2Fdashboard"));

    expect(response.headers.get("location")).toBeNull();
    expect(response.headers.get("x-middleware-next")).toBe("1");
  });
});
