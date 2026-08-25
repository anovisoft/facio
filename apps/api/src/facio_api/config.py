from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

TalkMode = Literal["scripted", "live"]
ProviderFamily = Literal["openai", "anthropic"]

HAIKU_MODEL = "claude-haiku-4-5"
GPT_DEFAULT_MODEL = "gpt-4o-mini"

MODEL_ALIASES: dict[str, str] = {
    "haiku": HAIKU_MODEL,
    "claude-haiku": HAIKU_MODEL,
    "anthropic": HAIKU_MODEL,
    "gpt": GPT_DEFAULT_MODEL,
    "openai": GPT_DEFAULT_MODEL,
}


class UnknownModelError(ValueError):
    """`FACIO_MODEL_NAME` does not map to a known provider family."""


def canonical_model(name: str) -> str:
    stripped = name.strip()
    return MODEL_ALIASES.get(stripped.casefold(), stripped)


def provider_family(model_name: str) -> ProviderFamily:
    """Pick OpenAI vs Anthropic from the model id (after aliases)."""
    resolved = canonical_model(model_name).casefold()
    if resolved.startswith("claude"):
        return "anthropic"
    if resolved.startswith(("gpt-", "gpt", "o1", "o3", "o4", "chatgpt")):
        return "openai"
    raise UnknownModelError(
        f"unknown model {model_name!r}: use gpt-4o-mini / haiku (claude-haiku-4-5)"
    )


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="FACIO_",
        extra="ignore",
        env_file=".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        protected_namespaces=(),
    )

    talk_mode: TalkMode = "scripted"
    model_name: str = GPT_DEFAULT_MODEL
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    anthropic_base_url: str = "https://api.anthropic.com"
    database_url: str = "postgresql+asyncpg://facio:facio@localhost:5432/facio"

    @field_validator("openai_api_key", "anthropic_api_key", mode="before")
    @classmethod
    def _blank_key(cls, value: object) -> object:
        if value == "":
            return None
        return value

    @property
    def resolved_model(self) -> str:
        return canonical_model(self.model_name)

    @property
    def family(self) -> ProviderFamily:
        return provider_family(self.model_name)

    def key_for(self, family: ProviderFamily) -> str | None:
        if family == "openai":
            return self.openai_api_key
        return self.anthropic_api_key


@lru_cache
def get_settings() -> Settings:
    return Settings()
