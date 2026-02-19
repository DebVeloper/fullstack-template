from collections.abc import AsyncGenerator

import pytest
from fastapi import APIRouter, FastAPI
from httpx import ASGITransport, AsyncClient

from app.main import register_exception_handlers


def create_test_app() -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)

    router = APIRouter()

    @router.get("/boom")
    async def boom() -> None:
        raise RuntimeError("unexpected failure")

    app.include_router(router)
    return app


@pytest.fixture
async def unhandled_client() -> AsyncGenerator[AsyncClient, None]:
    app = create_test_app()
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://testserver",
    ) as client:
        yield client


async def test_unhandled_exception_returns_internal_error_envelope(
    unhandled_client: AsyncClient,
) -> None:
    response = await unhandled_client.get("/boom")

    assert response.status_code == 500
    assert response.json() == {
        "error": {
            "code": "INTERNAL_ERROR",
            "message": "Internal server error",
            "details": None,
        }
    }
