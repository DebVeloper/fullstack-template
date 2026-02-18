import type { ReactElement } from "react";

import { UserTable } from "./user-table";

export function AdminUsersPanel(): ReactElement {
  return (
    <section className="admin-users-panel" aria-labelledby="admin-users-title">
      <header className="admin-users-panel__header">
        <h1 id="admin-users-title">Admin Users</h1>
        <p>Manage account lock, unlock, and soft delete actions.</p>
      </header>
      <UserTable />
    </section>
  );
}
