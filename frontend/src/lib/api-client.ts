import {
  createClient,
  createConfig,
  type Client,
  type ClientOptions,
  type CreateClientConfig
} from "@/client/client"

import { ApiError, type ApiErrorEnvelope } from "./api-error"

function toUnknownApiError(status: number): ApiError {
  return new ApiError(status, {
    code: "UNKNOWN_ERROR",
    message: `Request failed with status ${status}`,
    details: null
  })
}

const baseConfig = createConfig<ClientOptions>({
  baseUrl: ""
})

export const apiClient: Client = createClient(baseConfig)

apiClient.interceptors.response.use(async (response) => {
  if (response.ok) {
    return response
  }

  let body: ApiErrorEnvelope | null = null
  try {
    body = (await response.clone().json()) as ApiErrorEnvelope
  } catch {
    body = null
  }

  if (body?.error) {
    throw new ApiError(response.status, body.error)
  }

  throw toUnknownApiError(response.status)
})

export const createClientConfig: CreateClientConfig = (override) => ({
  ...baseConfig,
  ...override,
  baseUrl: ""
})
