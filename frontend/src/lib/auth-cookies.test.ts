import { describe, expect, it, vi } from "vitest";

import { clearAuthCookies, setAuthCookies } from "@/lib/auth-cookies";

interface MockCookieStore {
  set: ReturnType<typeof vi.fn>;
}

function createCookieStore(): MockCookieStore {
  return {
    set: vi.fn()
  };
}

describe("auth-cookies", () => {
  it("should set access and refresh cookies with secure auth defaults", () => {
    const cookieStore = createCookieStore();

    setAuthCookies(cookieStore, {
      access_token: "access-token",
      refresh_token: "refresh-token"
    });

    expect(cookieStore.set).toHaveBeenCalledTimes(2);
    expect(cookieStore.set).toHaveBeenNthCalledWith(
      1,
      "access_token",
      "access-token",
      expect.objectContaining({
        httpOnly: true,
        sameSite: "lax",
        path: "/",
        maxAge: 900
      })
    );
    expect(cookieStore.set).toHaveBeenNthCalledWith(
      2,
      "refresh_token",
      "refresh-token",
      expect.objectContaining({
        httpOnly: true,
        sameSite: "lax",
        path: "/api",
        maxAge: 604800
      })
    );
  });

  it("should clear access and refresh cookies", () => {
    const cookieStore = createCookieStore();

    clearAuthCookies(cookieStore);

    expect(cookieStore.set).toHaveBeenCalledTimes(2);
    expect(cookieStore.set).toHaveBeenNthCalledWith(
      1,
      "access_token",
      "",
      expect.objectContaining({
        path: "/",
        maxAge: 0
      })
    );
    expect(cookieStore.set).toHaveBeenNthCalledWith(
      2,
      "refresh_token",
      "",
      expect.objectContaining({
        path: "/api",
        maxAge: 0
      })
    );
  });
});
