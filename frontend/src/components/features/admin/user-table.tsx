"use client";

import type { ReactElement } from "react";

import { ApiError } from "@/lib/api-error";
import {
  type AdminUser,
  useAdminUsers,
  useLockAdminUser,
  useSoftDeleteAdminUser,
  useUnlockAdminUser
} from "@/hooks/queries/use-admin-users";
import { useCurrentUser } from "@/hooks/queries/use-current-user";

const SUPERADMIN_PROTECTED_REASON = "Superadmin account cannot be modified";

function normalizeEmail(email: string): string {
  return email.trim().toLowerCase();
}

function formatStatus(user: AdminUser): string {
  if (user.deleted_at) {
    return "Deleted";
  }

  if (user.is_active) {
    return "Active";
  }

  return "Locked";
}

export function UserTable(): ReactElement {
  const currentUserQuery = useCurrentUser();
  const usersQuery = useAdminUsers();
  const lockMutation = useLockAdminUser();
  const unlockMutation = useUnlockAdminUser();
  const deleteMutation = useSoftDeleteAdminUser();

  const activeAdminEmail =
    currentUserQuery.data?.is_admin === true
      ? normalizeEmail(currentUserQuery.data.email)
      : null;

  if (usersQuery.isPending) {
    return (
      <output className="admin-users__status" aria-live="polite">
        Loading users...
      </output>
    );
  }

  if (usersQuery.isError) {
    const message =
      usersQuery.error instanceof ApiError
        ? usersQuery.error.message
        : "Failed to load users.";

    return (
      <p className="admin-users__status admin-users__status--error" role="alert">
        {message}
      </p>
    );
  }

  const users = usersQuery.data?.items ?? [];

  if (users.length === 0) {
    return (
      <output className="admin-users__status" aria-live="polite">
        No users found.
      </output>
    );
  }

  const hasPendingMutation =
    lockMutation.isPending || unlockMutation.isPending || deleteMutation.isPending;

  async function onToggleLock(user: AdminUser): Promise<void> {
    if (user.is_active) {
      await lockMutation.mutateAsync(user.id);
      return;
    }

    await unlockMutation.mutateAsync(user.id);
  }

  async function onSoftDelete(userId: string): Promise<void> {
    await deleteMutation.mutateAsync(userId);
  }

  return (
    <div className="admin-users-table-wrap">
      <table className="admin-users-table">
        <thead>
          <tr>
            <th scope="col">Email</th>
            <th scope="col">Name</th>
            <th scope="col">Status</th>
            <th scope="col">Actions</th>
          </tr>
        </thead>
        <tbody>
          {users.map((user) => {
            const isSuperadminRow =
              activeAdminEmail !== null &&
              normalizeEmail(user.email) === activeAdminEmail;
            const isDeleted = user.deleted_at !== null;
            const lockLabel = user.is_active ? "Lock" : "Unlock";
            const disableActions = hasPendingMutation || isDeleted || isSuperadminRow;

            return (
              <tr key={user.id}>
                <td>{user.email}</td>
                <td>{user.name}</td>
                <td>{formatStatus(user)}</td>
                <td>
                  <div className="admin-users-table__actions">
                    <button
                      type="button"
                      className="admin-users-table__action admin-users-table__action--secondary"
                      disabled={disableActions}
                      onClick={() => {
                        void onToggleLock(user);
                      }}
                    >
                      {lockLabel}
                    </button>
                    <button
                      type="button"
                      className="admin-users-table__action admin-users-table__action--danger"
                      disabled={disableActions}
                      onClick={() => {
                        void onSoftDelete(user.id);
                      }}
                    >
                      Delete
                    </button>
                    {isSuperadminRow ? (
                      <p className="admin-users-table__reason">
                        {SUPERADMIN_PROTECTED_REASON}
                      </p>
                    ) : null}
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
