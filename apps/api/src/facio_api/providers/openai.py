from __future__ import annotations

import json
from typing import Any

import httpx

from facio_api.config import Settings
from facio_api.providers.types import ModelToolCall, ModelTurn
from facio_api.talk.spec import tool_schemas


class OpenAIProvider:
    def __init__(self, settings: Settings) -> None:
        if not settings.openai_api_key:
            raise ValueError("openai key missing")
        self._settings = settings

    async def complete(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> ModelTurn:
        headers = {
            "Authorization": f"Bearer {self._settings.openai_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._settings.resolved_model,
            "messages": messages,
            "tools": tools or tool_schemas(),
            "tool_choice": "auto",
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self._settings.openai_base_url.rstrip('/')}/chat/completions",
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
