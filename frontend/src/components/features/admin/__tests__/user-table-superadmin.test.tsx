import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useCurrentUser } from "@/hooks/queries/use-current-user";

import {
  useAdminUsers,
  useLockAdminUser,
  useDeleteAdminUser,
  useUnlockAdminUser
} from "@/hooks/queries/use-admin-users";

import { UserTable } from "../user-table";

vi.mock("@/hooks/queries/use-current-user", () => ({
  useCurrentUser: vi.fn()
}));

vi.mock("@/hooks/queries/use-admin-users", () => ({
  useAdminUsers: vi.fn(),
  useLockAdminUser: vi.fn(),
  useUnlockAdminUser: vi.fn(),
  useDeleteAdminUser: vi.fn()
}));

const useCurrentUserMock = vi.mocked(useCurrentUser);
const useAdminUsersMock = vi.mocked(useAdminUsers);
const useLockAdminUserMock = vi.mocked(useLockAdminUser);
const useUnlockAdminUserMock = vi.mocked(useUnlockAdminUser);
const useDeleteAdminUserMock = vi.mocked(useDeleteAdminUser);

const lockMutateAsync = vi.fn();
const unlockMutateAsync = vi.fn();
const deleteMutateAsync = vi.fn();

afterEach(() => {
  cleanup();
});

beforeEach(() => {
  vi.clearAllMocks();

  useCurrentUserMock.mockReturnValue({
    data: {
      id: "admin-user",
      email: " admin@example.com ",
      name: "Admin",
      picture_url: null,
      is_active: true,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
      is_admin: true
    }
  } as ReturnType<typeof useCurrentUser>);

  useAdminUsersMock.mockReturnValue({
    data: {
      items: [
        {
          id: "superadmin-row",
          email: "Admin@Example.com",
          name: "Super Admin",
          picture_url: null,
          is_active: true,
          created_at: "2026-01-01T00:00:00Z",
          updated_at: "2026-01-01T00:00:00Z",
          deleted_at: null
        },
        {
          id: "member-row",
          email: "member@example.com",
          name: "Member",
          picture_url: null,
          is_active: true,
          created_at: "2026-01-01T00:00:00Z",
          updated_at: "2026-01-01T00:00:00Z",
          deleted_at: null
        }
      ],
      total: 2,
      page: 1,
      size: 20,
      pages: 1
    },
    isPending: false,
    isError: false,
    error: null
  } as ReturnType<typeof useAdminUsers>);

  useLockAdminUserMock.mockReturnValue({
    mutateAsync: lockMutateAsync,
    isPending: false
  } as unknown as ReturnType<typeof useLockAdminUser>);

  useUnlockAdminUserMock.mockReturnValue({
    mutateAsync: unlockMutateAsync,
    isPending: false
  } as unknown as ReturnType<typeof useUnlockAdminUser>);

  useDeleteAdminUserMock.mockReturnValue({
    mutateAsync: deleteMutateAsync,
    isPending: false
  } as unknown as ReturnType<typeof useDeleteAdminUser>);
});

describe("UserTable superadmin guard", () => {
  it("should disable lock and delete actions for superadmin row with visible reason", () => {
    render(<UserTable />);

    const superadminCell = screen.getByRole("cell", { name: "Admin@Example.com" });
    const superadminRow = superadminCell.closest("tr");

    expect(superadminRow).not.toBeNull();
    if (!superadminRow) {
      return;
    }

    const rowScope = within(superadminRow);
    expect(rowScope.getByRole("button", { name: "Lock" })).toBeDisabled();
    expect(rowScope.getByRole("button", { name: "Delete" })).toBeDisabled();
    expect(
      rowScope.getByText("Superadmin account cannot be modified")
    ).toBeInTheDocument();
  });

  it("should allow lock and delete actions for non-superadmin rows", () => {
    render(<UserTable />);

    const memberCell = screen.getByRole("cell", { name: "member@example.com" });
    const memberRow = memberCell.closest("tr");

    expect(memberRow).not.toBeNull();
    if (!memberRow) {
      return;
    }

    const rowScope = within(memberRow);
    const lockButton = rowScope.getByRole("button", { name: "Lock" });
    const deleteButton = rowScope.getByRole("button", { name: "Delete" });

    expect(lockButton).toBeEnabled();
    expect(deleteButton).toBeEnabled();

    fireEvent.click(lockButton);
    fireEvent.click(deleteButton);

    expect(lockMutateAsync).toHaveBeenCalledWith("member-row");
    expect(deleteMutateAsync).toHaveBeenCalledWith("member-row");
    expect(unlockMutateAsync).not.toHaveBeenCalled();
  });

  it("should render unified error notice style when users query fails", () => {
    useAdminUsersMock.mockReturnValue({
      data: undefined,
      isPending: false,
      isError: true,
      error: new Error("network failure")
    } as ReturnType<typeof useAdminUsers>);

    render(<UserTable />);

    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent("Failed to load users.");
    expect(alert).toHaveClass("status-message");
    expect(alert).toHaveClass("status-message--error");
  });
});
