import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { useCurrentUser } from "@/hooks/queries/use-current-user";

import { Lnb } from "../lnb";

vi.mock("next/navigation", () => ({
  usePathname: vi.fn(() => "/dashboard")
}));

vi.mock("@/hooks/queries/use-current-user", () => ({
  useCurrentUser: vi.fn()
}));

const useCurrentUserMock = vi.mocked(useCurrentUser);

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("Lnb", () => {
  it("should hide Users menu when current user is not admin", () => {
    useCurrentUserMock.mockReturnValue({
      data: {
        id: "u-1",
        email: "member@example.com",
        name: "Member",
        picture_url: null,
        is_active: true,
        created_at: "2026-01-01T00:00:00Z",
        updated_at: "2026-01-01T00:00:00Z",
        is_admin: false
      }
    } as ReturnType<typeof useCurrentUser>);

    render(<Lnb />);

    expect(screen.getByRole("link", { name: "Dashboard" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Users" })).not.toBeInTheDocument();
  });

  it("should show Users menu when current user is admin", () => {
    useCurrentUserMock.mockReturnValue({
      data: {
        id: "u-2",
        email: "admin@example.com",
        name: "Admin",
        picture_url: null,
        is_active: true,
        created_at: "2026-01-01T00:00:00Z",
        updated_at: "2026-01-01T00:00:00Z",
        is_admin: true
      }
    } as ReturnType<typeof useCurrentUser>);

    render(<Lnb />);

    expect(screen.getByRole("link", { name: "Dashboard" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Users" })).toBeInTheDocument();
  });
});
