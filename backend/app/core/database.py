from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings
from app.models.base import Base

engine: AsyncEngine | None = None
async_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global engine
    if engine is None:
        settings = get_settings()
        engine = create_async_engine(settings.DATABASE_URL)
    return engine


def get_async_session_factory() -> async_sessionmaker[AsyncSession]:
    global async_session_factory
    if async_session_factory is None:
        async_session_factory = async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return async_session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with get_async_session_factory()() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def validate_database_schema() -> None:
    required_tables = {table.name for table in Base.metadata.sorted_tables}
    if not required_tables:
        return

    async with get_engine().connect() as connection:
        result = await connection.execute(
            text(
                "SELECT tablename FROM pg_catalog.pg_tables "
                "WHERE schemaname = ANY (current_schemas(false))"
            )
        )
        existing_tables = {str(row[0]) for row in result.fetchall()}

    missing_tables = sorted(required_tables - existing_tables)
    if not missing_tables:
        return

    missing_tables_label = ", ".join(missing_tables)
    msg = (
        "Database schema validation failed. "
        f"Missing tables: {missing_tables_label}. "
        "Run `uv run alembic upgrade head`."
    )
    raise RuntimeError(msg)
