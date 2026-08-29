"""A refused tool call must reach the model with its reason, and leave it a round to fix it.

The live hole: `add_cue(kind="timing", surface="timing")` came back as a bare
`invalid`, the turn could not tell what to change, and the sleep cue was lost.
No network here — a fake provider plays the two rounds.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from facio_domain.desk import founding_desk
from facio_domain.models import CueKind, CueSurface
from facio_domain.tools import CADENCE_REQUIRED, INVALID_KIND, INVALID_SURFACE

from facio_api.providers.types import ModelToolCall, ModelTurn
from facio_api.talk.loop import run_turn
from facio_api.talk.schemas import Locale, TalkTurnRequest

NOW = datetime(2026, 8, 15, 12, 0, 0)


def _request(utterance: str, locale: Locale = "ru") -> TalkTurnRequest:
    return TalkTurnRequest(
        utterance=utterance,
        desk=founding_desk(now=NOW),
        thread=[],
        thread_id="tool-errors",
        now=NOW,
        locale=locale,
    )


def _cue_call(call_id: str, kind: str, surface: str) -> ModelToolCall:
    return ModelToolCall(
        id=call_id,
        name="add_cue",
        arguments={
            "id": "bike-sleep-talk",
            "subject_id": "bike",
            "kind": kind,
            "text": "в 21 уже сплю",
            "surface": surface,
        },
    )


class SequenceProvider:
    """Plays scripted turns; after the script, closing text only."""

    def __init__(self, turns: list[ModelTurn]) -> None:
        self._turns = list(turns)
        self.complete_count = 0
        self.messages_at: list[list[dict[str, Any]]] = []

    async def complete(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> ModelTurn:
        del tools
        self.messages_at.append([dict(row) for row in messages])
        if self.complete_count >= len(self._turns):
            return ModelTurn(text="Готово.")
        turn = self._turns[self.complete_count]
        self.complete_count += 1
        return turn


def _tool_payloads(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [json.loads(row["content"]) for row in messages if row.get("role") == "tool"]


async def test_refused_kind_is_reported_then_the_retry_lands() -> None:
    provider = SequenceProvider(
        [
            ModelTurn(text=None, tool_calls=[_cue_call("call_1", "timing", "timing")]),
            ModelTurn(text=None, tool_calls=[_cue_call("call_2", "correction", "timing")]),
        ]
    )
    result = await run_turn(_request("напомни в 19, в 21 я уже сплю"), provider, now=NOW)

    assert provider.complete_count == 2
    first, second = result.tool_calls
    assert first.ok is False
    assert first.error == INVALID_KIND
    assert second.ok is True
    assert result.mutated is True

    cue = next(row for row in result.desk.cues if row.id == "bike-sleep-talk")
    assert cue.kind == CueKind.correction
    assert cue.surface == CueSurface.timing
    assert cue.text == "в 21 уже сплю"


async def test_the_refusal_reason_reaches_the_model_verbatim() -> None:
    provider = SequenceProvider(
        [
            ModelTurn(text=None, tool_calls=[_cue_call("call_1", "timing", "timing")]),
            ModelTurn(text=None, tool_calls=[_cue_call("call_2", "correction", "timing")]),
        ]
    )
    await run_turn(_request("напомни в 19, в 21 я уже сплю"), provider, now=NOW)

    payloads = _tool_payloads(provider.messages_at[1])
    assert payloads == [{"ok": False, "error": INVALID_KIND, "data": {}}]


def _gym_call(call_id: str, cadence: dict[str, Any] | None) -> ModelToolCall:
    arguments: dict[str, Any] = {"type": "counter", "title": "зал", "subject_id": "gym"}
    if cadence is not None:
        arguments["cadence"] = cadence
    return ModelToolCall(id=call_id, name="create_widget", arguments=arguments)


async def test_a_practice_with_no_rhythm_is_refused_then_the_retry_lands() -> None:
    """The live hole: «зал» landed with `cadence: none` nobody asked for.

    The law refuses instead of substituting a rhythm, names the missing field,
    and the same turn gets a round to say one out loud.
    """
    provider = SequenceProvider(
        [
            ModelTurn(text=None, tool_calls=[_gym_call("call_1", None)]),
            ModelTurn(text=None, tool_calls=[_gym_call("call_2", {"count": 2, "period": "week"})]),
        ]
    )
    result = await run_turn(_request("запиши зал"), provider, now=NOW)

    first, second = result.tool_calls
    assert first.ok is False
    assert first.error == CADENCE_REQUIRED
    assert second.ok is True
    assert result.mutated is True

    payloads = _tool_payloads(provider.messages_at[1])
    assert payloads == [{"ok": False, "error": CADENCE_REQUIRED, "data": {}}]

    gym = next(row for row in result.desk.subjects if row.id == "gym")
    assert gym.cadence.count == 2
    assert gym.cadence.period == "week"


async def test_a_refused_practice_leaves_no_half_written_subject() -> None:
    provider = SequenceProvider([ModelTurn(text=None, tool_calls=[_gym_call("call_1", None)])])
    result = await run_turn(_request("запиши зал"), provider, now=NOW)

    assert result.mutated is False
    assert result.tool_calls[0].error == CADENCE_REQUIRED
    assert "gym" not in {row.id for row in result.desk.subjects}
    assert not [row for row in result.desk.widgets if row.subject_id == "gym"]
    assert result.snapshots == []


async def test_a_bad_surface_names_the_surface_field_for_the_model() -> None:
    provider = SequenceProvider(
        [
            ModelTurn(text=None, tool_calls=[_cue_call("call_1", "correction", "rep-one")]),
            ModelTurn(text=None, tool_calls=[_cue_call("call_2", "correction", "do-time")]),
        ]
    )
    result = await run_turn(_request("держи корпус"), provider, now=NOW)

    payloads = _tool_payloads(provider.messages_at[1])
    assert payloads == [{"ok": False, "error": INVALID_SURFACE, "data": {}}]
    assert result.mutated is True
    cue = next(row for row in result.desk.cues if row.id == "bike-sleep-talk")
    assert cue.surface == CueSurface.do_time
