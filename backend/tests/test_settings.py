import importlib
from pathlib import Path

import pytest
from pydantic import ValidationError

ENV_KEYS = [
    "DATABASE_URL",
    "DATABASE_URL_TEST",
    "REDIS_URL",
    "SECRET_KEY",
    "ADMIN_EMAIL",
    "GOOGLE_OAUTH_CLIENT_ID",
    "GOOGLE_OAUTH_CLIENT_SECRET",
    "GOOGLE_OAUTH_REDIRECT_URI",
    "AUTH_TEST_MODE",
    "AUTH_TEST_SECRET",
    "ALLOWED_ORIGINS",
    "LOG_LEVEL",
    "LOG_JSON",
]


def clear_settings_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


def test_settings_loads_from_env_file_in_working_directory(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    clear_settings_env(monkeypatch)

    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/app",
                "DATABASE_URL_TEST=postgresql+asyncpg://postgres:postgres@localhost:5432/app_test",
                "REDIS_URL=redis://localhost:6379/0",
                "SECRET_KEY=test-secret",
                "ADMIN_EMAIL=admin@example.com",
                "GOOGLE_OAUTH_CLIENT_ID=test-client-id",
                "GOOGLE_OAUTH_CLIENT_SECRET=test-client-secret",
                "GOOGLE_OAUTH_REDIRECT_URI=http://localhost:3000/api/auth/google/callback",
                "AUTH_TEST_MODE=false",
                "ALLOWED_ORIGINS=http://localhost:3000,http://frontend:3000",
                "LOG_LEVEL=INFO",
                "LOG_JSON=false",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    config_module = importlib.import_module("app.core.config")
    settings = config_module.Settings()

    assert settings.DATABASE_URL.endswith("/app")
    assert settings.ALLOWED_ORIGINS == [
        "http://localhost:3000",
        "http://frontend:3000",
    ]


def test_settings_missing_required_env_raises_validation_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clear_settings_env(monkeypatch)

    config_module = importlib.import_module("app.core.config")

    with pytest.raises(ValidationError) as exc_info:
        config_module.Settings()

    assert "DATABASE_URL" in str(exc_info.value)


def test_settings_requires_auth_test_secret_when_test_mode_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clear_settings_env(monkeypatch)
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/app"
    )
    monkeypatch.setenv(
        "DATABASE_URL_TEST",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/app_test",
    )
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.setenv("ADMIN_EMAIL", "admin@example.com")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_SECRET", "test-client-secret")
    monkeypatch.setenv(
        "GOOGLE_OAUTH_REDIRECT_URI", "http://localhost:3000/api/auth/google/callback"
    )
    monkeypatch.setenv("AUTH_TEST_MODE", "true")
    monkeypatch.setenv("ALLOWED_ORIGINS", "http://localhost:3000")

    config_module = importlib.import_module("app.core.config")

    with pytest.raises(ValidationError) as exc_info:
        config_module.Settings()

    assert "AUTH_TEST_SECRET is required when AUTH_TEST_MODE=true" in str(
        exc_info.value
    )
