from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = (
        "postgresql+asyncpg://fasio:fasio@localhost:5435/fasio"
    )
    app_name: str = "Facio API"
    debug: bool = False
    # Comma-separated. Use "*" for any origin (credentials disabled).
    cors_origins: str = "*"

    anthropic_api_key: str | None = None
    llm_model: str = "claude-sonnet-5"
    llm_max_tokens: int = 8192
    # Anthropic prompt caching for stable system (+ create few-shots).
    llm_prompt_cache: bool = True
    llm_prompt_cache_ttl: Literal["5m", "1h"] = "5m"


@lru_cache
def get_settings() -> Settings:
    return Settings()
