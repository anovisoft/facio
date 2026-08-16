from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Protocol

import httpx

from facio_api.config import Settings
from facio_api.goldens import Golden, match_golden
from facio_api.spec import tool_schemas


@dataclass
class ModelToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class ModelTurn:
    text: str | None = None
    tool_calls: list[ModelToolCall] = field(default_factory=list)


class ModelProvider(Protocol):
    async def complete(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> ModelTurn: ...


class ScriptedProvider:
    """Plays a golden. Unknown utterances stay text — no invented patch."""

    def __init__(self, golden: Golden | None) -> None:
        self._turns = list(golden.scripted) if golden else []
        self._index = 0

    @classmethod
    def for_utterance(cls, utterance: str) -> ScriptedProvider:
        return cls(match_golden(utterance))

    async def complete(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> ModelTurn:
        del messages, tools
        if self._index >= len(self._turns):
            return ModelTurn(
                text="Скриптованный стенд знает только золотые реплики. Для живого рта нужен ключ модели на сервере."
            )
        step = self._turns[self._index]
        self._index += 1
        calls = [
            ModelToolCall(id=f"call_{self._index}_{offset}", name=call.name, arguments=call.arguments)
            for offset, call in enumerate(step.tool_calls)
        ]
        return ModelTurn(text=step.text, tool_calls=calls)


class OpenAIProvider:
    def __init__(self, settings: Settings) -> None:
        if not settings.model_api_key:
            raise ValueError("model key missing")
        self._settings = settings

    async def complete(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> ModelTurn:
        headers = {
            "Authorization": f"Bearer {self._settings.model_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._settings.model_name,
            "messages": messages,
            "tools": tools or tool_schemas(),
            "tool_choice": "auto",
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self._settings.model_base_url.rstrip('/')}/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            body = response.json()
        choice = body["choices"][0]["message"]
        calls: list[ModelToolCall] = []
        for raw in choice.get("tool_calls") or []:
            function = raw.get("function") or {}
            arguments = function.get("arguments") or "{}"
            parsed = json.loads(arguments) if isinstance(arguments, str) else dict(arguments)
            calls.append(
                ModelToolCall(
                    id=str(raw.get("id") or f"call_{len(calls)}"),
                    name=str(function.get("name") or ""),
                    arguments=parsed,
                )
            )
        text = choice.get("content")
        return ModelTurn(text=text if isinstance(text, str) else None, tool_calls=calls)


def provider_for(settings: Settings, utterance: str) -> ModelProvider:
    if settings.talk_mode == "scripted" or not settings.model_api_key:
        return ScriptedProvider.for_utterance(utterance)
    return OpenAIProvider(settings)
