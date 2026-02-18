import os
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.core.database import get_db
from app.core.redis import get_redis
from app.main import app
from app.models.base import Base
from app.models.user import User  # noqa: F401


class HealthyDBSession:
    async def execute(self, _query: object) -> None:
        return None


class FakeRedis:
    async def ping(self) -> bool:
        return True

    async def aclose(self) -> None:
        return None


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(scope="session")
def test_database_url() -> str:
    database_url_test = os.getenv("DATABASE_URL_TEST")
    if database_url_test is not None:
        return database_url_test

    return get_settings().DATABASE_URL_TEST


@pytest.fixture
async def db_session(test_database_url: str) -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(test_database_url)
    test_session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with test_session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
async def redis_session() -> AsyncGenerator[FakeRedis, None]:
    redis = FakeRedis()
    yield redis
    await redis.aclose()


@pytest.fixture
async def client(redis_session: FakeRedis) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db() -> AsyncGenerator[HealthyDBSession, None]:
        yield HealthyDBSession()

    async def override_get_redis() -> AsyncGenerator[FakeRedis, None]:
        yield redis_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as async_client:
        yield async_client

    app.dependency_overrides.clear()
