import { useQuery } from "@tanstack/react-query"

import { getApiV1UsersMe as getMe } from "@/client/sdk.gen"
import { apiClient } from "@/lib/api-client"

import { userKeys } from "./keys"

const CURRENT_USER_STALE_TIME = 60_000

export function useCurrentUser() {
  return useQuery({
    queryKey: userKeys.me(),
    queryFn: () => getMe({ client: apiClient }),
    staleTime: CURRENT_USER_STALE_TIME
  })
}
