from collections.abc import AsyncGenerator

from httpx import AsyncClient

from app.core.database import get_db
from app.core.redis import get_redis
from app.main import app


async def test_health_endpoint_returns_dependency_statuses_when_healthy(
    client: AsyncClient,
) -> None:
    response = await client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "db": True, "redis": True}


async def test_health_endpoint_returns_unhealthy_when_db_check_fails(
    client: AsyncClient,
) -> None:
    class FailingDBSession:
        async def execute(self, _query: object) -> None:
            raise RuntimeError("database unavailable")

    previous_override = app.dependency_overrides[get_db]

    async def override_get_db() -> AsyncGenerator[FailingDBSession, None]:
        yield FailingDBSession()

    app.dependency_overrides[get_db] = override_get_db
    try:
        response = await client.get("/api/v1/health")
    finally:
        app.dependency_overrides[get_db] = previous_override

    assert response.status_code == 503
    assert response.json() == {"status": "unhealthy", "db": False, "redis": True}


async def test_health_endpoint_returns_unhealthy_when_redis_check_fails(
    client: AsyncClient,
) -> None:
    class FailingRedis:
        async def ping(self) -> bool:
            raise RuntimeError("redis unavailable")

    previous_override = app.dependency_overrides[get_redis]

    async def override_get_redis() -> AsyncGenerator[FailingRedis, None]:
        yield FailingRedis()

    app.dependency_overrides[get_redis] = override_get_redis
    try:
        response = await client.get("/api/v1/health")
    finally:
        app.dependency_overrides[get_redis] = previous_override

    assert response.status_code == 503
    assert response.json() == {"status": "unhealthy", "db": True, "redis": False}
