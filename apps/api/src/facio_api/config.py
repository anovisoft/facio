from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="FACIO_", extra="ignore")

    talk_mode: Literal["scripted", "live"] = "scripted"
    model_api_key: str | None = None
    model_base_url: str = "https://api.openai.com/v1"
    model_name: str = "gpt-4o-mini"


@lru_cache
def get_settings() -> Settings:
    return Settings()
