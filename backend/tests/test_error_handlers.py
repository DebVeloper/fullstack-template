from collections.abc import AsyncGenerator
from typing import cast

import pytest
from fastapi import APIRouter, FastAPI
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel
from slowapi.errors import RateLimitExceeded
from slowapi.wrappers import Limit

from app.core.exceptions import BadRequestException
from app.main import register_exception_handlers


class ValidationPayload(BaseModel):
    name: str


class DummyRateLimit:
    error_message: str | None = "Too many requests"
    limit: str = "5/minute"


def create_test_app() -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)

    router = APIRouter()

    @router.get("/app-exception")
    async def raise_app_exception() -> None:
        raise BadRequestException(
            message="Bad request payload",
            details={"field": "name"},
        )

    @router.post("/validation")
    async def validate_payload(payload: ValidationPayload) -> dict[str, str]:
        return {"name": payload.name}

    @router.get("/rate-limit")
    async def raise_rate_limit() -> None:
        raise RateLimitExceeded(cast(Limit, DummyRateLimit()))

    app.include_router(router)
    return app


@pytest.fixture
async def error_client() -> AsyncGenerator[AsyncClient, None]:
    app = create_test_app()
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        yield client


async def test_app_exception_returns_unified_error_envelope(
    error_client: AsyncClient,
) -> None:
    response = await error_client.get("/app-exception")

    assert response.status_code == 400
    assert response.json() == {
        "error": {
            "code": "BAD_REQUEST",
            "message": "Bad request payload",
            "details": {"field": "name"},
        }
    }


async def test_validation_error_returns_unified_error_envelope(
    error_client: AsyncClient,
) -> None:
    response = await error_client.post("/validation", json={})

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["error"]["message"] == "Request validation failed"
    assert isinstance(body["error"]["details"], list)
    assert body["error"]["details"][0]["field"] == "name"


async def test_rate_limit_error_returns_unified_error_envelope(
    error_client: AsyncClient,
) -> None:
    response = await error_client.get("/rate-limit")

    assert response.status_code == 429
    assert response.json() == {
        "error": {
            "code": "RATE_LIMITED",
            "message": "Too many requests. Please try again later.",
            "details": None,
        }
    }
