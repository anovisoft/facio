from __future__ import annotations

from datetime import datetime

from facio_domain.desk import founding_desk
from facio_domain.models import CueSurface

from facio_api.goldens import load_goldens, match_golden
from facio_api.provider import ScriptedProvider
from facio_api.schemas import TalkTurnRequest
from facio_api.turn import run_turn

NOW = datetime(2026, 8, 15, 12, 0, 0)


def _request(utterance: str) -> TalkTurnRequest:
    return TalkTurnRequest(
        utterance=utterance,
        desk=founding_desk(now=NOW),
        thread=[],
        thread_id="golden",
        now=NOW,
    )


async def _play(utterance: str):
    return await run_turn(_request(utterance), ScriptedProvider.for_utterance(utterance), now=NOW)


def test_goldens_are_present() -> None:
    ids = {golden.id for golden in load_goldens()}
    assert ids == {"explain_only", "lower_back", "pain_raise"}


def test_match_lower_back() -> None:
    golden = match_golden("поясница забирает нагрузку")
    assert golden is not None
    assert golden.id == "lower_back"


async def test_lower_back_writes_do_time_cue() -> None:
    golden = match_golden("поясница забирает нагрузку")
    assert golden is not None
    result = await _play(golden.utterance)
    assert result.mutated is True
    assert [call.name for call in result.tool_calls] == golden.expect.tools
    cue = next(row for row in result.desk.cues if row.subject_id == "push-ups" and row.id.endswith("talk"))
    assert cue.surface == CueSurface.do_time
    for needle in golden.expect.cue.text_contains if golden.expect.cue else []:
        assert needle in cue.text
    assert result.snapshots
    assert result.snapshots[0].widget_id == "push-ups-counter"
    assert "корпус" in result.snapshots[0].line


async def test_pain_raise_does_not_lift_target() -> None:
    golden = match_golden("больно, давай 40")
    assert golden is not None
    result = await _play(golden.utterance)
    names = [call.name for call in result.tool_calls]
    assert names == golden.expect.tools
    assert result.tool_calls[0].ok is False
    assert result.tool_calls[0].error == "pain_forbids_raise"
    goal = next(row.target.goal for row in result.desk.subjects if row.id == "push-ups")
    assert goal <= (golden.expect.target_goal_max or 30)
    assert any(call.name == "add_cue" and call.ok for call in result.tool_calls)


async def test_explain_only_has_no_card() -> None:
    golden = match_golden("что значит держать корпус?")
    assert golden is not None
    result = await _play(golden.utterance)
    assert result.mutated is False
    assert result.snapshots == []
    assert result.tool_calls == []
    assert result.text
