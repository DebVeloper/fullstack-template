from typing import Literal

from pydantic import BaseModel


class RefreshRequest(BaseModel):
    refresh_token: str


class GoogleExchangeRequest(BaseModel):
    code: str
    code_verifier: str


class TestLoginRequest(BaseModel):
    email: str
    name: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"


class TokenPayload(BaseModel):
    sub: str
    exp: int
    iat: int
    type: Literal["access"]
