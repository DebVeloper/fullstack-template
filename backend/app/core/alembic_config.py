import os
from functools import lru_cache
from typing import ClassVar

from pydantic import ValidationError
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict as ConfigDict


class AlembicSettings(BaseSettings):
    model_config: ClassVar[ConfigDict] = ConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str


@lru_cache
def get_alembic_settings() -> AlembicSettings:
    return AlembicSettings()  # pyright: ignore[reportCallIssue]


def resolve_database_url(
    configured_url: str | None,
    env: dict[str, str] | None = None,
) -> str:
    environment = os.environ if env is None else env

    database_url = environment.get("DATABASE_URL")
    if database_url:
        return database_url

    if configured_url:
        return configured_url

    try:
        return get_alembic_settings().DATABASE_URL
    except ValidationError as exc:
        msg = "DATABASE_URL is required to run Alembic migrations"
        raise RuntimeError(msg) from exc
