from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Literal

LLMPurpose = Literal["create", "refine", "repair", "plugins"]


class LLMNotConfiguredError(RuntimeError):
    """Raised when no concrete LLM provider is configured."""


@dataclass(slots=True)
class LLMRawResult:
    model: str | None
    raw_response: Any
    tokens_in: int | None = None
    tokens_out: int | None = None
    latency_ms: int | None = None
    meta: dict[str, Any] = field(default_factory=dict)


class LLMProvider(ABC):
    @abstractmethod
    async def generate(
        self,
        *,
        purpose: LLMPurpose,
        messages: list[dict[str, Any]],
        response_schema: dict[str, Any],
    ) -> LLMRawResult:
        """Call the model and return the raw response (before app-level parse)."""


class NotConfiguredLLMProvider(LLMProvider):
    async def generate(
        self,
        *,
        purpose: LLMPurpose,
        messages: list[dict[str, Any]],
        response_schema: dict[str, Any],
    ) -> LLMRawResult:
        raise LLMNotConfiguredError(
            "LLM provider is not configured. "
            "Wire a concrete LLMProvider implementation to enable "
            f"'{purpose}'."
        )


_llm_provider: LLMProvider | None = None


def get_llm_provider() -> LLMProvider:
    global _llm_provider
    if _llm_provider is None:
        _llm_provider = NotConfiguredLLMProvider()
    return _llm_provider


def set_llm_provider(provider: LLMProvider) -> None:
    global _llm_provider
    _llm_provider = provider
