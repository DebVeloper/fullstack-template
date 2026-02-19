from __future__ import annotations

from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from alembic import context
from app.core.alembic_config import resolve_database_url
from app.models.base import Base
from app.models.user import User  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_database_url() -> str:
    return resolve_database_url(config.get_main_option("sqlalchemy.url"))


def run_migrations_offline() -> None:
    database_url = get_database_url()
    config.set_main_option("sqlalchemy.url", database_url)

    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    database_url = get_database_url()
    config.set_main_option("sqlalchemy.url", database_url)

    connectable = create_async_engine(
        database_url,
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    from asyncio import run

    run(run_migrations_online())
