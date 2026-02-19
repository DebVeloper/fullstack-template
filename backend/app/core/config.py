from functools import lru_cache
from typing import Annotated, ClassVar

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode
from pydantic_settings import SettingsConfigDict as ConfigDict


class Settings(BaseSettings):
    model_config: ClassVar[ConfigDict] = ConfigDict(env_file=".env")

    DATABASE_URL: str
    DATABASE_URL_TEST: str
    REDIS_URL: str
    SECRET_KEY: str
    ADMIN_EMAIL: str
    GOOGLE_OAUTH_CLIENT_ID: str
    GOOGLE_OAUTH_CLIENT_SECRET: str
    GOOGLE_OAUTH_REDIRECT_URI: str
    AUTH_TEST_MODE: bool = False
    AUTH_TEST_SECRET: str | None = None
    ALLOWED_ORIGINS: Annotated[list[str], NoDecode]
    LOG_LEVEL: str = "INFO"
    LOG_JSON: bool = False

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_allowed_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, list):
            return [origin.strip() for origin in value if origin.strip()]

        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]

        raise TypeError("ALLOWED_ORIGINS must be a comma-separated string or list")

    @model_validator(mode="after")
    def validate_auth_test_secret(self) -> "Settings":
        if self.AUTH_TEST_MODE and not self.AUTH_TEST_SECRET:
            raise ValueError("AUTH_TEST_SECRET is required when AUTH_TEST_MODE=true")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()  # pyright: ignore[reportCallIssue]
