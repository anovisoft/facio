"""Anthropic Claude LLMProvider with structured JSON outputs."""

from __future__ import annotations

import copy
import json
import time
from typing import Any, Literal

import anthropic

from app.providers.llm import LLMProvider, LLMPurpose, LLMRawResult

CacheTtl = Literal["5m", "1h"]

# Create few-shots occupy the first 4 chat turns (user/assistant × 2).
_CREATE_FEWSHOT_CHAT_LEN = 4


class AnthropicLLMProvider(LLMProvider):
    def __init__(
        self,
        *,
        api_key: str,
        model: str = "claude-sonnet-5",
        max_tokens: int = 8192,
        prompt_cache: bool = True,
        prompt_cache_ttl: CacheTtl = "5m",
    ) -> None:
        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._model = model
        self._max_tokens = max_tokens
        self._prompt_cache = prompt_cache
        self._prompt_cache_ttl = prompt_cache_ttl

    async def generate(
        self,
        *,
        purpose: LLMPurpose,
        messages: list[dict[str, Any]],
        response_schema: dict[str, Any],
    ) -> LLMRawResult:
        system, chat_messages = _split_system(messages)
        schema = _anthropic_json_schema(response_schema)
        cache_ctrl = (
            _cache_control(self._prompt_cache_ttl) if self._prompt_cache else None
        )

        if cache_ctrl and system:
            system_payload: str | list[dict[str, Any]] = [
                {
                    "type": "text",
                    "text": system,
                    "cache_control": cache_ctrl,
                }
            ]
        else:
            system_payload = system  # type: ignore[assignment]

        api_messages = _to_api_messages(
            chat_messages,
            purpose=purpose,
            cache_control=cache_ctrl,
        )

        started = time.perf_counter()
        kwargs: dict[str, Any] = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "messages": api_messages,
            "output_config": {
                "format": {
                    "type": "json_schema",
                    "schema": schema,
                }
            },
        }
        if system_payload:
            kwargs["system"] = system_payload

        response = await self._client.messages.create(**kwargs)
        latency_ms = int((time.perf_counter() - started) * 1000)

        text = _extract_text(response)
        raw_response: Any = json.loads(text)

        usage = getattr(response, "usage", None)
        tokens_in = getattr(usage, "input_tokens", None) if usage else None
        tokens_out = getattr(usage, "output_tokens", None) if usage else None
        cache_read = (
            getattr(usage, "cache_read_input_tokens", None) if usage else None
        )
        cache_write = (
            getattr(usage, "cache_creation_input_tokens", None) if usage else None
        )

        return LLMRawResult(
            model=self._model,
            raw_response=raw_response,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            latency_ms=latency_ms,
            meta={
                "stop_reason": getattr(response, "stop_reason", None),
                "prompt_cache": self._prompt_cache,
                "cache_read_input_tokens": cache_read,
                "cache_creation_input_tokens": cache_write,
            },
        )


def _cache_control(ttl: CacheTtl) -> dict[str, str]:
    if ttl == "1h":
        return {"type": "ephemeral", "ttl": "1h"}
    return {"type": "ephemeral"}


def _split_system(
    messages: list[dict[str, Any]],
) -> tuple[str | None, list[dict[str, Any]]]:
    system_parts: list[str] = []
    chat: list[dict[str, Any]] = []
    for msg in messages:
        role = msg.get("role")
        content = msg.get("content", "")
        if role == "system":
            if isinstance(content, str) and content.strip():
                system_parts.append(content)
            continue
        if role not in {"user", "assistant"}:
            raise ValueError(f"Unsupported message role for Anthropic: {role!r}")
        chat.append({"role": role, "content": content})
    if not chat:
        raise ValueError("Anthropic messages must include at least one user turn")
    system = "\n\n".join(system_parts) if system_parts else None
    return system, chat


def _to_api_messages(
    chat_messages: list[dict[str, Any]],
    *,
    purpose: LLMPurpose,
    cache_control: dict[str, str] | None,
) -> list[dict[str, Any]]:
    """Convert chat turns; optionally cache create few-shot prefix."""
    out: list[dict[str, Any]] = []
    cache_idx: int | None = None
    if (
        cache_control
        and purpose == "create"
        and len(chat_messages) >= _CREATE_FEWSHOT_CHAT_LEN
    ):
        # Last few-shot assistant turn — stable across intents and retries.
        cache_idx = _CREATE_FEWSHOT_CHAT_LEN - 1

    for i, msg in enumerate(chat_messages):
        content = msg["content"]
        if not isinstance(content, str):
            content = json.dumps(content, ensure_ascii=False)
        block: dict[str, Any] = {"type": "text", "text": content}
        if cache_control and i == cache_idx:
            block["cache_control"] = cache_control
        out.append({"role": msg["role"], "content": [block]})
    return out


def _extract_text(response: Any) -> str:
    parts: list[str] = []
    for block in getattr(response, "content", []) or []:
        if getattr(block, "type", None) == "text":
            parts.append(getattr(block, "text", "") or "")
    text = "".join(parts).strip()
    if not text:
        raise ValueError("Anthropic response contained no text content")
    return text


def _anthropic_json_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Normalize Pydantic JSON Schema for Anthropic structured outputs."""
    out = copy.deepcopy(schema)
    _transform_schema_node(out)
    if "type" not in out and "properties" in out:
        out["type"] = "object"
    return out


_STRIP_KEYS = {
    "minimum",
    "maximum",
    "exclusiveMinimum",
    "exclusiveMaximum",
    "multipleOf",
    "minLength",
    "maxLength",
    "minItems",
    "maxItems",
    "minProperties",
    "maxProperties",
    "pattern",
    "format",
    "title",
    "default",
}


def _transform_schema_node(node: Any) -> None:
    if not isinstance(node, dict):
        return
    for key in list(node.keys()):
        if key in _STRIP_KEYS:
            del node[key]
    props = node.get("properties")
    if node.get("type") == "object" or isinstance(props, dict):
        node.setdefault("additionalProperties", False)
        if isinstance(props, dict) and props:
            # Anthropic structured outputs expect every property listed in required
            node["required"] = list(props.keys())
            # Transform each property schema — do NOT walk `properties` itself
            # as a schema node: stripping metadata key "title" would delete the
            # real field named "title" (PathGroup / PathAction / checklist).
            for prop_schema in props.values():
                _transform_schema_node(prop_schema)
    for key, value in node.items():
        if key == "properties":
            continue
        if isinstance(value, dict):
            _transform_schema_node(value)
        elif isinstance(value, list):
            for item in value:
                _transform_schema_node(item)
