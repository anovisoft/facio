from __future__ import annotations

from datetime import datetime
from typing import Any

from facio_domain.desk import founding_desk
from facio_domain.models import CueSurface

from facio_api.providers.scripted import ScriptedProvider
from facio_api.providers.types import ModelToolCall, ModelTurn
from facio_api.talk.loop import EMPTY_TOOLS_NUDGE, run_turn
from facio_api.talk.schemas import TalkTurnRequest

NOW = datetime(2026, 8, 15, 12, 0, 0)
UNKNOWN = "квэкснутый зонд 174"


def _add_cue_call() -> ModelToolCall:
    return ModelToolCall(
        id="call_cue",
        name="add_cue",
        arguments={
            "id": "push-ups-nudge-talk",
            "subject_id": "push-ups",
            "kind": "correction",
            "text": "держи корпус",
            "surface": "do-time",
        },
    )


def _request(utterance: str) -> TalkTurnRequest:
    return TalkTurnRequest(
        utterance=utterance,
        desk=founding_desk(now=NOW),
        thread=[],
        thread_id="nudge",
        now=NOW,
    )


class SequenceProvider:
    """Plays scripted completes. After the script, closing text only — not counted."""

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


def _nudge_in(messages: list[dict[str, Any]]) -> bool:
    return any(row.get("role") == "user" and row.get("content") == EMPTY_TOOLS_NUDGE for row in messages)


class CountingProvider:
    def __init__(self, inner: ScriptedProvider) -> None:
        self._inner = inner
        self.complete_count = 0

    async def complete(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> ModelTurn:
        self.complete_count += 1
        return await self._inner.complete(messages, tools)


async def test_text_only_first_complete_nudges_then_add_cue() -> None:
    provider = SequenceProvider(
        [
            ModelTurn(text="Сейчас запишу."),
            ModelTurn(text=None, tool_calls=[_add_cue_call()]),
        ]
    )
    result = await run_turn(_request("держи корпус"), provider, now=NOW)
    assert result.mutated is True
    assert provider.complete_count == 2
    assert not _nudge_in(provider.messages_at[0])
    assert _nudge_in(provider.messages_at[1])
    cue = next(row for row in result.desk.cues if row.id == "push-ups-nudge-talk")
    assert cue.subject_id == "push-ups"
    assert cue.surface == CueSurface.do_time
    assert "add_cue" in [call.name for call in result.tool_calls]


async def test_tools_on_first_complete_do_not_nudge() -> None:
    provider = SequenceProvider(
        [
            ModelTurn(text=None, tool_calls=[_add_cue_call()]),
        ]
    )
    result = await run_turn(_request("держи корпус"), provider, now=NOW)
    assert result.mutated is True
    assert provider.complete_count == 1
    assert all(not _nudge_in(rows) for rows in provider.messages_at)
    assert any(row.id == "push-ups-nudge-talk" for row in result.desk.cues)


async def test_unknown_stays_unmutated_after_nudge() -> None:
    provider = CountingProvider(ScriptedProvider.for_utterance(UNKNOWN))
    result = await run_turn(_request(UNKNOWN), provider, now=NOW)
    assert result.mutated is False
    assert result.tool_calls == []
    assert provider.complete_count == 2


async def test_leaked_rules_are_stripped_from_user_text() -> None:
    leak = (
        "Понял. Записываю: реплика → инструменты сразу по умолчаниям "
        "(focused_widget или виджет Сегодня)."
    )
    provider = SequenceProvider([ModelTurn(text=leak), ModelTurn(text=leak)])
    result = await run_turn(_request("верни велосипед"), provider, now=NOW)
    assert result.mutated is False
    assert "инструмент" not in result.text.casefold()
    assert "focused_widget" not in result.text
    assert result.text == "Записал бы на стол — напиши ещё раз короче."
