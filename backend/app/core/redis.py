from collections.abc import AsyncGenerator

from redis.asyncio import ConnectionPool, Redis

from app.core.config import get_settings

pool: ConnectionPool | None = None


def get_redis_pool() -> ConnectionPool:
    global pool
    if pool is None:
        settings = get_settings()
        pool = ConnectionPool.from_url(settings.REDIS_URL, decode_responses=True)
    return pool


async def get_redis() -> AsyncGenerator[Redis, None]:
    redis = Redis(connection_pool=get_redis_pool())
    try:
        yield redis
    finally:
        await redis.aclose()
