const usersRootKey = ["users"] as const;
const adminUsersRootKey = ["admin-users"] as const;
const adminUsersListKey = [...adminUsersRootKey, "list"] as const;

export interface AdminUsersListQuery {
  page: number;
  size: number;
  include_deleted: boolean;
}

export const userKeys = {
  all: usersRootKey,
  me: () => [...usersRootKey, "me"] as const
};

export const adminUserKeys = {
  all: adminUsersRootKey,
  lists: () => adminUsersListKey,
  list: (query: AdminUsersListQuery) => [...adminUsersListKey, query] as const
};
