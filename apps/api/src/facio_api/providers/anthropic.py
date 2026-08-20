from __future__ import annotations

import json
from typing import Any

import httpx

from facio_api.config import Settings
from facio_api.providers.types import ModelToolCall, ModelTurn
from facio_api.talk.spec import tool_schemas

ANTHROPIC_VERSION = "2023-06-01"
ANTHROPIC_MAX_TOKENS = 4096


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
