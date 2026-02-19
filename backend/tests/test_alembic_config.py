from pathlib import Path

import pytest

from app.core.alembic_config import get_alembic_settings, resolve_database_url


@pytest.fixture(autouse=True)
def clear_alembic_settings_cache() -> None:
    get_alembic_settings.cache_clear()


def test_resolve_database_url_returns_env_database_url_first() -> None:
    database_url = resolve_database_url(
        configured_url="postgresql+asyncpg://from-configured-url",
        env={"DATABASE_URL": "postgresql+asyncpg://from-env"},
    )

    assert database_url == "postgresql+asyncpg://from-env"


def test_resolve_database_url_returns_configured_url_when_env_is_missing() -> None:
    database_url = resolve_database_url(
        configured_url="postgresql+asyncpg://from-configured-url",
        env={},
    )

    assert database_url == "postgresql+asyncpg://from-configured-url"


def test_resolve_database_url_loads_from_dotenv_when_env_and_config_are_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/app\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    database_url = resolve_database_url(configured_url=None, env={})

    assert database_url == "postgresql+asyncpg://postgres:postgres@localhost:5432/app"


def test_resolve_database_url_ignores_non_database_keys_in_dotenv(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/app",
                "SECRET_KEY=test-secret",
                "REDIS_URL=redis://localhost:6379/0",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    database_url = resolve_database_url(configured_url=None, env={})

    assert database_url == "postgresql+asyncpg://postgres:postgres@localhost:5432/app"


def test_resolve_database_url_raises_runtime_error_when_all_sources_are_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)

    with pytest.raises(RuntimeError) as exc_info:
        resolve_database_url(configured_url=None, env={})

    assert str(exc_info.value) == "DATABASE_URL is required to run Alembic migrations"
