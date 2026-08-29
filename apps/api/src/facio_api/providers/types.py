from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


class LiveProviderError(Exception):
    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


@dataclass
class ModelToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class ModelTurn:
    text: str | None = None
    tool_calls: list[ModelToolCall] = field(default_factory=list)
    # What the vendor billed for this round. Empty for scripted. The cache
    # fields in here are the only ground truth that prompt caching still
    # works — it fails silently, by costing more, never by erroring.
    usage: dict[str, Any] = field(default_factory=dict)


class ModelProvider(Protocol):
    async def complete(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> ModelTurn: ...
