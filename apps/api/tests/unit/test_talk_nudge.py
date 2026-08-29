from __future__ import annotations

from datetime import datetime
from typing import Any

from facio_domain.desk import founding_desk
from facio_domain.models import CueSurface

from facio_api.providers.scripted import ScriptedProvider
from facio_api.providers.types import ModelToolCall, ModelTurn
from facio_api.talk.loop import EMPTY_TOOLS_NUDGE, EMPTY_TOOLS_NUDGE_EN, LOCALE_LINE, run_turn
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


def _en_request(utterance: str) -> TalkTurnRequest:
    return TalkTurnRequest(
        utterance=utterance,
        desk=founding_desk(now=NOW),
        thread=[],
        thread_id="nudge-en",
        now=NOW,
        locale="en",
    )


def test_system_prompt_is_english_and_bilingual() -> None:
    """В1.6 bullets, rewritten in English; Russian examples kept and paired with English."""
    from facio_api.talk.spec import SYSTEM_PROMPT

    assert SYSTEM_PROMPT.startswith("You sit across the Facio desk.")
    assert "Answer in the person's language" in SYSTEM_PROMPT
    for english in ("the gym shuts at 22", "didn't go today", "make it once a week"):
        assert english in SYSTEM_PROMPT
    for russian in ("зал до 22", "сегодня не сходил", "давай раз в неделю"):
        assert russian in SYSTEM_PROMPT


def test_pain_skip_bullet_repeats_the_skip_subject_default() -> None:
    """E2b: the pain bullet must not leave the subject to guesswork — same default, both languages."""
    from facio_api.talk.spec import SYSTEM_PROMPT

    bullet = next(row for row in SYSTEM_PROMPT.splitlines() if row.startswith("- Pain plus a skip"))
    assert "bike / bike-reminder" in bullet
    assert "never push-ups" in bullet
    assert "either language" in bullet


async def test_locale_line_rides_the_turn_system_prompt() -> None:
    provider = SequenceProvider([ModelTurn(text=None, tool_calls=[_add_cue_call()])])
    await run_turn(_en_request("brace the core"), provider, now=NOW)
    system = [row["content"] for row in provider.messages_at[0] if row.get("role") == "system"]
    assert LOCALE_LINE["en"] in system
    assert LOCALE_LINE["ru"] not in system

    ru_provider = SequenceProvider([ModelTurn(text=None, tool_calls=[_add_cue_call()])])
    await run_turn(_request("держи корпус"), ru_provider, now=NOW)
    ru_system = [row["content"] for row in ru_provider.messages_at[0] if row.get("role") == "system"]
    assert LOCALE_LINE["ru"] in ru_system


async def test_english_turn_gets_the_english_nudge() -> None:
    provider = SequenceProvider(
        [
            ModelTurn(text="Noting that now."),
            ModelTurn(text=None, tool_calls=[_add_cue_call()]),
        ]
    )
    result = await run_turn(_en_request("brace the core"), provider, now=NOW)
    assert result.mutated is True
    assert provider.complete_count == 2
    nudges = [
        row.get("content")
        for row in provider.messages_at[1]
        if row.get("role") == "user" and row.get("content") in {EMPTY_TOOLS_NUDGE, EMPTY_TOOLS_NUDGE_EN}
    ]
    assert nudges == [EMPTY_TOOLS_NUDGE_EN]


async def test_leaked_rules_fall_back_in_english() -> None:
    leak = "Sure. I will call the tool_call with the focused_widget default."
    provider = SequenceProvider([ModelTurn(text=leak), ModelTurn(text=leak)])
    result = await run_turn(_en_request("bring the bike back"), provider, now=NOW)
    assert result.mutated is False
    assert "tool_call" not in result.text
    assert result.text == "I would put that on the desk — say it once more, shorter."
