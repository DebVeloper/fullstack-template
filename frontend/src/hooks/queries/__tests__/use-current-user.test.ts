import { renderHook, waitFor } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { setupServer } from "msw/node"
import { afterAll, afterEach, beforeAll, describe, expect, it } from "vitest"

import { apiClient } from "@/lib/api-client"
import { createWrapper } from "@/tests/utils"

import { useCurrentUser } from "../use-current-user"

const server = setupServer()

beforeAll(() => {
  server.listen()
  apiClient.setConfig({ baseUrl: "http://localhost:3000" })
})
afterEach(() => server.resetHandlers())
afterAll(() => {
  apiClient.setConfig({ baseUrl: "" })
  server.close()
})

describe("useCurrentUser", () => {
  it("should fetch current user data", async () => {
    server.use(
      http.get("/api/v1/users/me", () => {
        return HttpResponse.json({
          id: "user-1",
          email: "test@example.com",
          name: "Test User",
          is_active: true,
          is_verified: true,
          is_admin: false,
          created_at: "2026-01-01T00:00:00Z",
          updated_at: "2026-01-01T00:00:00Z"
        })
      })
    )

    const { result } = renderHook(() => useCurrentUser(), {
      wrapper: createWrapper()
    })

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true)
    })

    expect(result.current.data?.email).toBe("test@example.com")
  })
})
