from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    debug: bool = False
    app_name: str = "SocialSim4 Backend"
    api_prefix: str = "/api"

    backend_host: str = "0.0.0.0"
    backend_port: int = 8000

    database_url: str = "sqlite+aiosqlite:///./socialsim4.db"
    redis_url: str | None = None

    jwt_signing_key: SecretStr = SecretStr("change-me")
    jwt_algorithm: str = "HS256"
    access_token_exp_minutes: int = 15
    refresh_token_exp_minutes: int = 60 * 24 * 14

    email_smtp_url: str | None = None
    email_from: str | None = None

    allowed_origins: list[str] = []

    model_config = SettingsConfigDict(
        extra="ignore",
        env_prefix="SOCIALSIM4_",
        env_file=".env",
        env_file_encoding="utf-8",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
