"""Anthropic structured turn. Key and retry live here; Path does not."""

from __future__ import annotations

import copy
import json
from typing import Any, Protocol

import anthropic
from facio_domain.models import Cue, Subject, Widget
from pydantic import ValidationError

from facio_api.patches import LlmTurnWire, PatchRejected, TurnOut, wire_to_turn

_MAX_ATTEMPTS = 2

_SYSTEM = """You edit one focused practice. Return only a short confirmation and patches.

Allowed ops:
- add_cue: kind, text, surface. surface is required. correction → do-time. clarification → on-demand.
- set_target: goal (and optional current).
- set_cadence: count >= 1, period day|week.
- shrink: shrink_cadence week (once a week) or none (drop cadence). Never raise.
- none: explain only; confirmation is enough.

Empty string / -1 means the field is unused.

Do not create widgets. Do not invent a freeform payload.
If the person reports pain, injury, or the lower back taking the load: do not raise target or cadence. You may add a technique cue or shrink.
Founding case: "поясница забирает нагрузку" on push-ups → add_cue correction do-time about bracing the core and the glutes. Not a higher target.
Confirmation: one short line the person can read. Not medical advice.
"""


class TurnGenerator(Protocol):
    async def generate(
        self,
        *,
        utterance: str,
        subject: Subject,
        cues: list[Cue],
        widget: Widget,
    ) -> TurnOut: ...


class AnthropicTurnGenerator:
    def __init__(self, *, api_key: str, model: str = "claude-haiku-4-5") -> None:
        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._model = model

    async def generate(
        self,
        *,
        utterance: str,
        subject: Subject,
        cues: list[Cue],
        widget: Widget,
    ) -> TurnOut:
        user = _user_payload(utterance, subject, cues, widget)
        messages: list[dict[str, Any]] = [{"role": "user", "content": user}]
        schema = _anthropic_json_schema(LlmTurnWire.model_json_schema())
        last_error: Exception | None = None

        for attempt in range(_MAX_ATTEMPTS):
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=1024,
                system=_SYSTEM,
                messages=messages,
                output_config={"format": {"type": "json_schema", "schema": schema}},
            )
            text = _extract_text(response)
            try:
                raw = json.loads(text)
                wire = LlmTurnWire.model_validate(raw)
                return wire_to_turn(wire)
            except (json.JSONDecodeError, ValidationError, PatchRejected, ValueError) as exc:
                last_error = exc
                if attempt + 1 >= _MAX_ATTEMPTS:
                    break
                messages = [
                    *messages,
                    {"role": "assistant", "content": text},
                    {
                        "role": "user",
                        "content": (
                            f"Previous response failed validation: {exc}. "
                            "Return corrected JSON matching the schema. "
                            "add_cue must include surface."
                        ),
                    },
                ]

        raise PatchRejected(f"invalid model output: {last_error}")


def _user_payload(utterance: str, subject: Subject, cues: list[Cue], widget: Widget) -> str:
    context = {
        "utterance": utterance,
        "subject": subject.model_dump(mode="json"),
        "cues": [cue.model_dump(mode="json") for cue in cues],
        "widget": widget.model_dump(mode="json"),
    }
    return json.dumps(context, ensure_ascii=False)


def _extract_text(response: Any) -> str:
    parts: list[str] = []
    for block in getattr(response, "content", []) or []:
        if getattr(block, "type", None) == "text":
            parts.append(getattr(block, "text", "") or "")
    text = "".join(parts).strip()
    if not text:
        raise PatchRejected("Anthropic response contained no text")
    return text


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
    "description",
}


def _anthropic_json_schema(schema: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(schema)
    _transform_schema_node(out)
    if "type" not in out and "properties" in out:
        out["type"] = "object"
    return out


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
            node["required"] = list(props.keys())
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
