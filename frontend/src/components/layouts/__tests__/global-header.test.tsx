import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useCurrentUser } from "@/hooks/queries/use-current-user";

import { GlobalHeader } from "../global-header";

const pushMock = vi.fn();
const refreshMock = vi.fn();
const fetchMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: vi.fn(() => ({
    push: pushMock,
    refresh: refreshMock
  }))
}));

vi.mock("@/hooks/queries/use-current-user", () => ({
  useCurrentUser: vi.fn()
}));

const useCurrentUserMock = vi.mocked(useCurrentUser);

beforeEach(() => {
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("GlobalHeader", () => {
  it("should show current user profile information", () => {
    useCurrentUserMock.mockReturnValue({
      data: {
        id: "u-1",
        email: "member@example.com",
        name: "Member User",
        picture_url: null,
        is_active: true,
        created_at: "2026-01-01T00:00:00Z",
        updated_at: "2026-01-01T00:00:00Z",
        is_admin: false
      }
    } as ReturnType<typeof useCurrentUser>);

    render(<GlobalHeader />);

    expect(screen.getByRole("link", { name: "Atlas Console" })).toBeInTheDocument();
    expect(screen.getByText("Member User")).toBeInTheDocument();
    expect(screen.getByText("member@example.com")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Logout" })).toBeInTheDocument();
  });

  it("should call logout route and redirect to login on logout click", async () => {
    useCurrentUserMock.mockReturnValue({
      data: {
        id: "u-2",
        email: "admin@example.com",
        name: "Admin User",
        picture_url: null,
        is_active: true,
        created_at: "2026-01-01T00:00:00Z",
        updated_at: "2026-01-01T00:00:00Z",
        is_admin: true
      }
    } as ReturnType<typeof useCurrentUser>);
    fetchMock.mockResolvedValue(new Response(null, { status: 204 }));

    render(<GlobalHeader />);
    fireEvent.click(screen.getByRole("button", { name: "Logout" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith("/api/auth/logout", {
        method: "POST"
      });
    });
    expect(pushMock).toHaveBeenCalledWith("/login");
    expect(refreshMock).toHaveBeenCalledTimes(1);
  });
});
