from collections.abc import Awaitable
from inspect import isawaitable
from typing import Annotated, Any, cast

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.redis import get_redis

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check(
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> JSONResponse:
    db_ok = False
    redis_ok = False

    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False

    try:
        ping_result = redis.ping()
        if isawaitable(ping_result):
            await cast(Awaitable[Any], ping_result)
        elif ping_result is False:
            raise RuntimeError("redis ping failed")
        redis_ok = True
    except Exception:
        redis_ok = False

    status = "healthy" if db_ok and redis_ok else "unhealthy"
    status_code = 200 if status == "healthy" else 503

    return JSONResponse(
        status_code=status_code,
        content={"status": status, "db": db_ok, "redis": redis_ok},
    )
