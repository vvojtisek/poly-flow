from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="POLYFLOW_", env_file=".env", extra="ignore")

    env: str = "dev"
    log_level: str = "INFO"
    database_url: str = "postgresql+asyncpg://polyflow:polyflow@localhost:5432/polyflow"
    redis_url: str = "redis://localhost:6379/0"
    cors_origins: list[str] = ["http://localhost:3000"]
    readiness_timeout_s: float = 2.0
    piper_url: str = "http://localhost:5000"
    whisper_url: str = "http://localhost:9000"


@lru_cache
def get_settings() -> Settings:
    return Settings()
