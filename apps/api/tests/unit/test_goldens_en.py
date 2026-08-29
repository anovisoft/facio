"""English goldens: the same desk locks as the Russian set, on English utterances."""

from __future__ import annotations

from datetime import datetime, time

import pytest

from facio_domain.desk import founding_desk
from facio_domain.models import CueSurface, Desk, SubjectStatus, WidgetType
from facio_domain.tools import apply_tool, times_per_week

from facio_api.providers.scripted import ScriptedProvider
from facio_api.talk.goldens import Golden, load_goldens, match_golden
from facio_api.talk.loop import run_turn
from facio_api.talk.schemas import TalkTurnRequest

NOW = datetime(2026, 8, 15, 12, 0, 0)
FOUNDING_BRACE = "brace the core and the glutes"
FOUNDING_IDS = {"bike", "push-ups", "vegetables"}
UNKNOWN_EN = "quaxnuted probe 174"
RUSSIAN_IDS = {
    "cadence_shrink",
    "explain_only",
    "gym_no_clock",
    "gym_until_22",
    "lower_back",
    "method_4_to_30",
    "miss_skip",
    "named_hour_beats_closing",
    "pain_raise",
    "pain_skip_freeze",
    "remind_at_19",
    "thaw_pause",
}


def _request(utterance: str) -> TalkTurnRequest:
    return TalkTurnRequest(
        utterance=utterance,
        desk=founding_desk(now=NOW),
        thread=[],
        thread_id="golden-en",
        now=NOW,
        locale="en",
    )


async def _play(utterance: str):
    return await run_turn(_request(utterance), ScriptedProvider.for_utterance(utterance), now=NOW)


def _names(result) -> list[str]:
    return [call.name for call in result.tool_calls]


def _subject(desk: Desk, subject_id: str):
    return next(row for row in desk.subjects if row.id == subject_id)


def _sentences(text: str) -> list[str]:
    chunks = text.replace("!", ".").replace("?", ".").split(".")
    return [part.strip() for part in chunks if part.strip()]


def _needles(golden: Golden) -> list[str]:
    return [row.casefold() for row in (golden.match or [golden.utterance])]


# --- the set itself -------------------------------------------------------


def test_every_russian_golden_has_an_english_mirror() -> None:
    ids = {golden.id for golden in load_goldens()}
    assert {f"{row}_en" for row in RUSSIAN_IDS} <= ids


def test_english_goldens_carry_no_cyrillic_utterance() -> None:
    for golden in load_goldens():
        if not golden.id.endswith("_en"):
            continue
        blob = golden.utterance + "".join(golden.match)
        assert not any("Ѐ" <= char <= "ӿ" for char in blob), golden.id


def test_needles_never_overlap() -> None:
    """`match_golden` takes the first file by sorted name — needles must be disjoint."""
    goldens = load_goldens()
    clashes: list[tuple[str, str, str, str]] = []
    for left in goldens:
        for right in goldens:
            if left.id >= right.id:
                continue
            for a in _needles(left):
                for b in _needles(right):
                    if a in b or b in a:
                        clashes.append((left.id, a, right.id, b))
    assert clashes == []


@pytest.mark.parametrize("golden", load_goldens(), ids=lambda row: row.id)
def test_each_utterance_and_needle_routes_home(golden: Golden) -> None:
    assert match_golden(golden.utterance) is not None
    assert match_golden(golden.utterance).id == golden.id
    for needle in golden.match or [golden.utterance]:
        matched = match_golden(needle)
        assert matched is not None
        assert matched.id == golden.id


async def test_unknown_english_utterance_stays_text_only() -> None:
    assert match_golden(UNKNOWN_EN) is None
    result = await _play(UNKNOWN_EN)
    assert result.mutated is False
    assert result.tool_calls == []
    assert result.snapshots == []


# --- founding three -------------------------------------------------------


async def test_lower_back_en_writes_do_time_cue() -> None:
    golden = match_golden("my lower back takes the load")
    assert golden is not None
    assert golden.id == "lower_back_en"
    result = await _play(golden.utterance)
    assert result.mutated is True
    assert _names(result) == golden.expect.tools
    cue = next(row for row in result.desk.cues if row.subject_id == "push-ups" and row.id.endswith("en-talk"))
    assert cue.surface == CueSurface.do_time
    for needle in golden.expect.cue.text_contains if golden.expect.cue else []:
        assert needle in cue.text
    assert result.snapshots
    assert result.snapshots[0].widget_id == "push-ups-counter"


async def test_pain_raise_en_does_not_lift_target() -> None:
    golden = match_golden("it hurts, let's do 40")
    assert golden is not None
    assert golden.id == "pain_raise_en"
    result = await _play(golden.utterance)
    assert _names(result) == golden.expect.tools
    assert result.tool_calls[0].ok is False
    assert result.tool_calls[0].error == "pain_forbids_raise"
    goal = next(row.target.goal for row in result.desk.subjects if row.id == "push-ups")
    assert goal <= (golden.expect.target_goal_max or 30)
    assert any(call.name == "add_cue" and call.ok for call in result.tool_calls)


async def test_explain_only_en_has_no_card() -> None:
    golden = match_golden("what does keeping the core tight mean?")
    assert golden is not None
    assert golden.id == "explain_only_en"
    result = await _play(golden.utterance)
    assert result.mutated is False
    assert result.snapshots == []
    assert result.tool_calls == []
    assert result.text


# --- В1.2 six -------------------------------------------------------------


async def test_method_4_to_30_en_writes_current_and_cue() -> None:
    golden = match_golden("I can do 4, I want 30 in a row, how?")
    assert golden is not None
    assert golden.id == "method_4_to_30_en"
    result = await _play(golden.utterance)
    names = _names(result)
    assert result.mutated is True
    assert names[0] in {"list_desk", "get_widget", "get_subject"}
    assert "update_widget" in names
    assert "add_cue" in names
    for name in golden.expect.forbidden_tools:
        assert name not in names
    update = next(call for call in result.tool_calls if call.name == "update_widget")
    assert update.arguments["widget_id"] == "push-ups-counter"
    assert update.arguments["target"] == 30
    assert update.arguments["count"] == 4
    push = _subject(result.desk, "push-ups")
    assert push.target is not None
    assert push.target.current == 4
    assert push.target.goal == 30
    assert times_per_week(push.cadence) <= 3
    cue = next(row for row in result.desk.cues if row.subject_id == "push-ups" and row.id.endswith("en-talk"))
    assert cue.surface == CueSurface.do_time
    assert cue.text != FOUNDING_BRACE
    for needle in golden.expect.cue.text_contains if golden.expect.cue else []:
        assert needle in cue.text
    assert any(card.widget_id == "push-ups-counter" for card in result.snapshots)
    assert len(_sentences(result.text)) >= 2


async def test_gym_no_clock_en_creates_counter_without_reminder() -> None:
    golden = match_golden("put the gym on the desk")
    assert golden is not None
    assert golden.id == "gym_no_clock_en"
    result = await _play(golden.utterance)
    names = _names(result)
    assert result.mutated is True
    assert "create_widget" in names
    assert "set_reminder" not in names
    create = next(call for call in result.tool_calls if call.name == "create_widget")
    assert create.arguments["type"] == "counter"
    subject_id = create.arguments["subject_id"]
    assert subject_id not in FOUNDING_IDS
    reminders = [
        row for row in result.desk.widgets if row.subject_id == subject_id and row.type == WidgetType.reminder
    ]
    assert reminders == []
    bike = _subject(result.desk, "bike")
    assert bike.window is not None
    assert bike.window.latest_by == time(19, 0)


async def test_miss_skip_en_does_not_hang_a_clock() -> None:
    golden = match_golden("didn't go today")
    assert golden is not None
    assert golden.id == "miss_skip_en"
    result = await _play(golden.utterance)
    names = _names(result)
    assert result.mutated is True
    assert "skip" in names
    assert "set_reminder" not in names
    skip = next(call for call in result.tool_calls if call.name == "skip")
    assert skip.ok is True
    assert skip.arguments["widget_id"] == "bike-reminder"
    bike = _subject(result.desk, "bike")
    assert bike.window is not None
    assert bike.window.latest_by == time(19, 0)


async def test_remind_at_19_en_uses_stated_hour() -> None:
    golden = match_golden("remind me at 19, I am asleep by 21")
    assert golden is not None
    assert golden.id == "remind_at_19_en"
    result = await _play(golden.utterance)
    names = _names(result)
    assert result.mutated is True
    reminder = next(call for call in result.tool_calls if call.name == "set_reminder")
    assert reminder.arguments["subject_id"] == "bike"
    assert reminder.arguments["latest_by"] in {"19:00", "19:00:00"}
    assert reminder.arguments.get("closes_at") not in {"21:00", "21:00:00"}
    bike = _subject(result.desk, "bike")
    assert bike.window is not None
    assert bike.window.latest_by == time(19, 0)
    assert bike.window.latest_by != time(18, 0)
    timing = [
        row for row in result.desk.cues if row.subject_id == "bike" and row.surface == CueSurface.timing
    ]
    assert any("asleep" in row.text.casefold() for row in timing)
    assert "add_cue" in names


async def test_gym_until_22_en_is_arithmetic() -> None:
    golden = match_golden("the gym shuts at 22")
    assert golden is not None
    assert golden.id == "gym_until_22_en"
    result = await _play(golden.utterance)
    assert result.mutated is True
    reminder = next(call for call in result.tool_calls if call.name == "set_reminder")
    assert reminder.arguments["closes_at"] in {"22:00", "22:00:00"}
    assert "latest_by" not in reminder.arguments
    bike = _subject(result.desk, "bike")
    assert bike.window is not None
    assert bike.window.latest_by == time(19, 0)
    assert bike.window.closes_at == time(22, 0)


async def test_named_hour_beats_closing_en_formula() -> None:
    golden = match_golden("by 23 it already closes. Remind me to go to the gym at 19")
    assert golden is not None
    assert golden.id == "named_hour_beats_closing_en"
    result = await _play(golden.utterance)
    assert result.mutated is True
    reminder = next(call for call in result.tool_calls if call.name == "set_reminder")
    assert reminder.arguments["latest_by"] in {"19:00", "19:00:00"}
    assert reminder.arguments["closes_at"] in {"23:00", "23:00:00"}
    gym = _subject(result.desk, reminder.arguments["subject_id"])
    assert gym.window is not None
    assert gym.window.latest_by == time(19, 0)
    assert gym.window.closes_at == time(23, 0)
    fire = next(
        row.payload.fire_at
        for row in result.desk.widgets
        if row.subject_id == gym.id and row.type == WidgetType.reminder
    )
    assert fire is not None
    assert fire.hour == 19


async def test_cadence_shrink_en_does_not_raise_goal() -> None:
    golden = match_golden("make it once a week")
    assert golden is not None
    assert golden.id == "cadence_shrink_en"
    result = await _play(golden.utterance)
    names = _names(result)
    assert result.mutated is True
    assert names[0] in {"shrink_subject", "set_cadence"}
    shrink = next(call for call in result.tool_calls if call.name == "shrink_subject")
    assert shrink.arguments["subject_id"] == "push-ups"
    push = _subject(result.desk, "push-ups")
    assert times_per_week(push.cadence) <= 1
    assert push.target is not None
    assert push.target.goal <= 30


# --- В2.3 freeze / thaw ---------------------------------------------------


async def test_pain_skip_freeze_en_pauses_bike_without_raising() -> None:
    golden = match_golden("skipped today, my back hurt")
    assert golden is not None
    assert golden.id == "pain_skip_freeze_en"
    assert "didn't go today" not in golden.utterance
    result = await _play(golden.utterance)
    names = _names(result)
    assert result.mutated is True
    assert names == golden.expect.tools
    for name in golden.expect.forbidden_tools:
        assert name not in names
    skip = next(call for call in result.tool_calls if call.name == "skip")
    assert skip.arguments["widget_id"] == "bike-reminder"
    freeze = next(call for call in result.tool_calls if call.name == "freeze_subject")
    assert freeze.arguments["subject_id"] == "bike"
    assert freeze.ok is True
    bike = _subject(result.desk, "bike")
    assert bike.status == SubjectStatus.paused
    assert bike.paused_at == NOW
    push = _subject(result.desk, "push-ups")
    assert push.target is not None
    assert push.target.goal <= 30


def test_match_thaw_phrases_en() -> None:
    assert match_golden("it eased off").id == "thaw_pause_en"
    assert match_golden("the back is fine now").id == "thaw_pause_en"
    assert match_golden("bring the bike back").id == "thaw_pause_en"


async def test_thaw_pause_en_restores_bike() -> None:
    golden = match_golden("it eased off")
    assert golden is not None
    assert golden.id == "thaw_pause_en"
    frozen = apply_tool(
        founding_desk(now=NOW),
        "freeze_subject",
        {"subject_id": "bike"},
        pain=False,
        now=NOW,
    )
    assert frozen.ok
    result = await run_turn(
        TalkTurnRequest(
            utterance=golden.utterance,
            desk=frozen.desk,
            thread=[],
            thread_id="golden-en",
            now=NOW,
            locale="en",
        ),
        ScriptedProvider.for_utterance(golden.utterance),
        now=NOW,
    )
    assert result.mutated is True
    assert _names(result) == golden.expect.tools
    bike = _subject(result.desk, "bike")
    assert bike.status == SubjectStatus.active
    assert bike.paused_at is None
