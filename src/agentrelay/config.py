"""Application settings via pydantic-settings."""

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    DATABASE_URL: str = "postgresql+asyncpg://localhost/agentrelay"
    DEBUG: bool = False
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:3001", "http://localhost:5173"]
    APP_ENV: str = "development"
    SECRET_KEY: str = ""
    RATE_LIMIT_MAX_REQUESTS: int = 60
    RATE_LIMIT_WINDOW_SECONDS: int = 60
    REDIS_URL: str = "redis://localhost:6379/0"
    BATCH_MAX_SIZE: int = 100
    ENABLE_REGENERATOR: bool = False

    @model_validator(mode="after")
    def _normalize_database_url(self) -> "Settings":
        """Render provides postgres:// but asyncpg needs postgresql+asyncpg://."""
        url = self.DATABASE_URL
        if url.startswith("postgres://"):
            self.DATABASE_URL = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://"):
            self.DATABASE_URL = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return self


settings = Settings()
