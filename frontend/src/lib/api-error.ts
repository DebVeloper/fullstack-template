export interface ApiErrorDetail {
  code: string
  message: string
  details: unknown
}

export interface ApiErrorEnvelope {
  error?: ApiErrorDetail
}

export class ApiError extends Error {
  readonly status: number
  readonly code: string
  readonly details: unknown

  constructor(status: number, error: ApiErrorDetail) {
    super(error.message)
    this.name = "ApiError"
    this.status = status
    this.code = error.code
    this.details = error.details
  }
}
