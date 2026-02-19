import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ApiError, type ApiErrorEnvelope } from "@/lib/api-error";

import { adminUserKeys, type AdminUsersListQuery } from "./keys";

const ADMIN_USERS_PATH = "/api/v1/admin/users";
const ADMIN_USERS_STALE_TIME = 30_000;

export interface AdminUser {
  id: string;
  email: string;
  name: string;
  picture_url: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
}

export interface AdminUsersListResponse {
  items: AdminUser[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface UseAdminUsersOptions {
  page?: number;
  size?: number;
}

function normalizeQuery(options: UseAdminUsersOptions): AdminUsersListQuery {
  return {
    page: options.page ?? 1,
    size: options.size ?? 20
  };
}

function buildAdminUsersUrl(query: AdminUsersListQuery): string {
  const searchParams = new URLSearchParams();
  searchParams.set("page", String(query.page));
  searchParams.set("size", String(query.size));

  return `${ADMIN_USERS_PATH}?${searchParams.toString()}`;
}

function createUnknownError(status: number): ApiError {
  return new ApiError(status, {
    code: "UNKNOWN_ERROR",
    message: `Request failed with status ${status}`,
    details: null
  });
}

async function toApiError(response: Response): Promise<ApiError> {
  try {
    const body = (await response.json()) as ApiErrorEnvelope;
    if (body?.error) {
      return new ApiError(response.status, body.error);
    }
  } catch {
  }

  return createUnknownError(response.status);
}

async function requestJson<T>(input: string, init?: RequestInit): Promise<T> {
  const response = await fetch(input, init);

  if (!response.ok) {
    throw await toApiError(response);
  }

  return (await response.json()) as T;
}

async function fetchAdminUsers(query: AdminUsersListQuery): Promise<AdminUsersListResponse> {
  return requestJson<AdminUsersListResponse>(buildAdminUsersUrl(query), {
    method: "GET",
    cache: "no-store"
  });
}

async function lockAdminUser(userId: string): Promise<AdminUser> {
  return requestJson<AdminUser>(`${ADMIN_USERS_PATH}/${userId}/lock`, {
    method: "PATCH"
  });
}

async function unlockAdminUser(userId: string): Promise<AdminUser> {
  return requestJson<AdminUser>(`${ADMIN_USERS_PATH}/${userId}/unlock`, {
    method: "PATCH"
  });
}

async function deleteAdminUser(userId: string): Promise<AdminUser> {
  return requestJson<AdminUser>(`${ADMIN_USERS_PATH}/${userId}`, {
    method: "DELETE"
  });
}

export function useAdminUsers(options: UseAdminUsersOptions = {}) {
  const query = normalizeQuery(options);

  return useQuery({
    queryKey: adminUserKeys.list(query),
    queryFn: () => fetchAdminUsers(query),
    staleTime: ADMIN_USERS_STALE_TIME
  });
}

export function useLockAdminUser() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: lockAdminUser,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: adminUserKeys.lists() });
    }
  });
}

export function useUnlockAdminUser() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: unlockAdminUser,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: adminUserKeys.lists() });
    }
  });
}

export function useDeleteAdminUser() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: deleteAdminUser,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: adminUserKeys.lists() });
    }
  });
}
