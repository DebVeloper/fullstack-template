from typing import Any

from pydantic import BaseModel

ErrorDetails = dict[str, Any] | list[dict[str, Any]] | None


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: ErrorDetails = None


class ErrorResponse(BaseModel):
    error: ErrorDetail
