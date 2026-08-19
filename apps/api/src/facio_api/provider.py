from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Protocol

import httpx

from facio_api.config import Settings, UnknownModelError, provider_family
from facio_api.goldens import Golden, match_golden
from facio_api.spec import tool_schemas

ANTHROPIC_VERSION = "2023-06-01"
ANTHROPIC_MAX_TOKENS = 4096


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


class AnthropicProvider:
    def __init__(self, settings: Settings) -> None:
        if not settings.anthropic_api_key:
            raise ValueError("anthropic key missing")
        self._settings = settings

    async def complete(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> ModelTurn:
        system, chat = openai_messages_to_anthropic(messages)
        payload: dict[str, Any] = {
            "model": self._settings.resolved_model,
            "max_tokens": ANTHROPIC_MAX_TOKENS,
            "messages": chat,
            "tools": openai_tools_to_anthropic(tools or tool_schemas()),
        }
        if system:
            payload["system"] = system
        headers = {
            "x-api-key": self._settings.anthropic_api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "content-type": "application/json",
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self._settings.anthropic_base_url.rstrip('/')}/v1/messages",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            body = response.json()
        return anthropic_body_to_turn(body)


def openai_tools_to_anthropic(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    converted: list[dict[str, Any]] = []
    for tool in tools:
        function = tool.get("function") if tool.get("type") == "function" else tool
        if not isinstance(function, dict):
            continue
        parameters = function.get("parameters") or {"type": "object", "properties": {}}
        converted.append(
            {
                "name": str(function.get("name") or ""),
                "description": str(function.get("description") or ""),
                "input_schema": parameters,
            }
        )
    return converted


def openai_messages_to_anthropic(messages: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
    """Map the turn loop's OpenAI-shaped messages onto Anthropic Messages."""
    system_parts: list[str] = []
    chat: list[dict[str, Any]] = []
    pending_results: list[dict[str, Any]] = []

    def flush_results() -> None:
        if not pending_results:
            return
        _append_chat(chat, {"role": "user", "content": list(pending_results)})
        pending_results.clear()

    for message in messages:
        role = message.get("role")
        if role == "system":
            flush_results()
            text = message.get("content")
            if isinstance(text, str) and text.strip():
                system_parts.append(text)
            continue
        if role == "tool":
            pending_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": str(message.get("tool_call_id") or ""),
                    "content": message.get("content") or "",
                }
            )
            continue
        flush_results()
        if role == "assistant":
            _append_chat(chat, {"role": "assistant", "content": _assistant_content(message)})
            continue
        _append_chat(chat, {"role": "user", "content": message.get("content") or ""})

    flush_results()
    if chat and chat[0]["role"] != "user":
        chat.insert(0, {"role": "user", "content": "."})
    return "\n\n".join(system_parts), chat


def anthropic_body_to_turn(body: dict[str, Any]) -> ModelTurn:
    calls: list[ModelToolCall] = []
    text_parts: list[str] = []
    for block in body.get("content") or []:
        kind = block.get("type")
        if kind == "text":
            piece = block.get("text")
            if isinstance(piece, str) and piece:
                text_parts.append(piece)
            continue
        if kind == "tool_use":
            raw_input = block.get("input") or {}
            arguments = raw_input if isinstance(raw_input, dict) else {}
            calls.append(
                ModelToolCall(
                    id=str(block.get("id") or f"call_{len(calls)}"),
                    name=str(block.get("name") or ""),
                    arguments=arguments,
                )
            )
    text = "\n".join(text_parts) or None
    return ModelTurn(text=text, tool_calls=calls)


def _assistant_content(message: dict[str, Any]) -> str | list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    text = message.get("content")
    if isinstance(text, str) and text:
        blocks.append({"type": "text", "text": text})
    for raw in message.get("tool_calls") or []:
        function = raw.get("function") or {}
        arguments = function.get("arguments") or "{}"
        parsed = json.loads(arguments) if isinstance(arguments, str) else dict(arguments)
        blocks.append(
            {
                "type": "tool_use",
                "id": str(raw.get("id") or f"toolu_{len(blocks)}"),
                "name": str(function.get("name") or ""),
                "input": parsed,
            }
        )
    if not blocks:
        return ""
    if len(blocks) == 1 and blocks[0]["type"] == "text":
        return blocks[0]["text"]
    return blocks


def _append_chat(chat: list[dict[str, Any]], item: dict[str, Any]) -> None:
    if chat and chat[-1]["role"] == item["role"]:
        chat[-1]["content"] = _merge_content(chat[-1]["content"], item["content"])
        return
    chat.append(item)


def _merge_content(left: str | list[Any], right: str | list[Any]) -> str | list[Any]:
    if isinstance(left, str) and isinstance(right, str):
        return f"{left}\n{right}".strip()
    return _as_blocks(left) + _as_blocks(right)


def _as_blocks(content: str | list[Any]) -> list[Any]:
    if isinstance(content, list):
        return list(content)
    if not content:
        return []
    return [{"type": "text", "text": content}]


def provider_for(settings: Settings, utterance: str) -> ModelProvider:
    if settings.talk_mode != "live":
        return ScriptedProvider.for_utterance(utterance)
    try:
        family = provider_family(settings.model_name)
    except UnknownModelError as error:
        raise LiveProviderError(str(error)) from error
    key = settings.key_for(family)
    if not key:
        raise LiveProviderError(f"{family} key missing")
    if family == "anthropic":
        return AnthropicProvider(settings)
    return OpenAIProvider(settings)
