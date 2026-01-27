"""Server configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Server settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database connection
    database_url: str = "postgresql://localhost/openattribution"

    # Server
    port: int = 8007
    debug: bool = False
    log_level: str = "INFO"


settings = Settings()
