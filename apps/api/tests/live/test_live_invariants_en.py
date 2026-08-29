"""English mirror of the live invariants: desk locks, not tool sequences or verbatim text."""

from __future__ import annotations

from datetime import datetime, time

import pytest

from facio_domain.desk import founding_desk
from facio_domain.models import CueKind, CueSurface, Desk, SubjectStatus, WidgetType
from facio_domain.tools import times_per_week

from facio_api.talk.schemas import TalkSelection, TalkTurnResponse

pytestmark = pytest.mark.live

SEED_BRACE = "держи корпус и ягодицы"
FOUNDING_BRACE = "brace the core and the glutes"
FOUNDING_IDS = {"bike", "push-ups", "vegetables"}
FOUNDING_PUSH_WEEKLY = 3.0
FOUNDING_PUSH_GOAL = 30
NOW = datetime(2026, 8, 15, 12, 0, 0)


def _names(result: TalkTurnResponse) -> list[str]:
    return [call.name for call in result.tool_calls]


def _subject(desk: Desk, subject_id: str):
    rows = [row for row in desk.subjects if row.id == subject_id]
    assert rows, f"no subject {subject_id}"
    return rows[0]


def _hhmm(value: object) -> tuple[int, int] | None:
    if value is None:
        return None
    if isinstance(value, time):
        return (value.hour, value.minute)
    text = str(value).strip()
    parts = text.split(":")
    if not parts or not parts[0].isdigit():
        return None
    hour = int(parts[0])
    minute = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
    return (hour, minute)


def _assert_english(result: TalkTurnResponse) -> None:
    """The language rule is a lock, not a wording check: no Cyrillic back at an English turn."""
    cyrillic = [char for char in result.text if "Ѐ" <= char <= "ӿ"]
    assert cyrillic == [], result.text


async def test_method_4_to_30_lands_current_and_cue(live_play_en) -> None:
    result = await live_play_en("I can do 4, I want 30 in a row, how?")
    names = _names(result)
    assert result.mutated is True
    assert "set_reminder" not in names
    push = _subject(result.desk, "push-ups")
    assert push.target is not None
    assert push.target.current == 4
    assert push.target.goal == 30
    assert times_per_week(push.cadence) <= FOUNDING_PUSH_WEEKLY
    method_cues = [
        row
        for row in result.desk.cues
        if row.subject_id == "push-ups"
        and row.surface == CueSurface.do_time
        and row.text != SEED_BRACE
        and row.text != FOUNDING_BRACE
    ]
    # The progression changes how it is done — a correction seen at rep one, not
    # a clarification filed behind a «?» ([04] Cue defaults).
    assert method_cues
    assert all(row.kind == CueKind.correction for row in method_cues)
    assert result.snapshots
    assert result.text
    _assert_english(result)


async def test_gym_no_clock_creates_counter_without_reminder(live_play_en) -> None:
    result = await live_play_en("put the gym on the desk")
    names = _names(result)
    assert result.mutated is True
    assert "set_reminder" not in names
    created = [
        call
        for call in result.tool_calls
        if call.name == "create_widget"
        and call.ok
        and call.arguments.get("type") == "counter"
        and call.arguments.get("subject_id") not in FOUNDING_IDS
    ]
    # A refusal leaves the desk untouched, so only a call that landed counts.
    assert created, [(call.name, call.error) for call in result.tool_calls]
    subject_id = created[-1].arguments["subject_id"]
    reminders = [
        row for row in result.desk.widgets if row.subject_id == subject_id and row.type == WidgetType.reminder
    ]
    assert reminders == []
    # A new practice arrives with a rhythm named in the same call ([06] #14).
    # `none` is legal for a one-off; a gym is not one.
    assert isinstance(created[-1].arguments.get("cadence"), dict), created[-1].arguments
    gym = _subject(result.desk, subject_id)
    assert gym.cadence.period in {"day", "week"}, gym.cadence
    assert times_per_week(gym.cadence) >= 1
    bike = _subject(result.desk, "bike")
    assert bike.window is not None
    assert bike.window.latest_by == time(19, 0)
    assert any(row.id == "bike-reminder" for row in result.desk.widgets)
    _assert_english(result)


async def test_miss_skip_does_not_hang_a_clock(live_play_en) -> None:
    result = await live_play_en("didn't go today")
    names = _names(result)
    assert result.mutated is True
    assert any(call.name == "skip" and call.ok for call in result.tool_calls)
    assert "set_reminder" not in names
    bike = _subject(result.desk, "bike")
    assert bike.window is not None
    assert bike.window.latest_by == time(19, 0)
    _assert_english(result)


async def test_remind_at_19_uses_stated_hour(live_play_en) -> None:
    result = await live_play_en("remind me at 19, I am asleep by 21")
    names = _names(result)
    assert result.mutated is True
    for call in result.tool_calls:
        if call.name != "set_reminder":
            continue
        assert _hhmm(call.arguments.get("closes_at")) != (21, 0)
    bike = _subject(result.desk, "bike")
    assert bike.window is not None
    assert bike.window.latest_by == time(19, 0)
    assert bike.window.latest_by != time(18, 0)
    timing = [
        row
        for row in result.desk.cues
        if row.subject_id == "bike" and row.surface == CueSurface.timing
    ]
    assert any("sleep" in row.text.casefold() for row in timing)
    assert "add_cue" in names
    _assert_english(result)


async def test_gym_until_22_is_arithmetic(live_play_en) -> None:
    result = await live_play_en("the gym shuts at 22")
    assert result.mutated is True
    doors = [
        call
        for call in result.tool_calls
        if call.name == "set_reminder" and _hhmm(call.arguments.get("closes_at")) == (22, 0)
    ]
    assert doors, _names(result)
    assert _hhmm(doors[0].arguments.get("latest_by")) != (19, 0)
    bike = _subject(result.desk, "bike")
    assert bike.window is not None
    assert bike.window.closes_at == time(22, 0)
    assert bike.window.latest_by == time(19, 0)
    _assert_english(result)


NAMED_HOUR_AND_DOOR_EN = (
    "I want to go to the gym but I keep forgetting about it and by 23 it is already closed. "
    "Remind me that I need to go to the gym at 19"
)


async def test_named_hour_beats_closing_formula(live_play_en) -> None:
    result = await live_play_en(NAMED_HOUR_AND_DOOR_EN)
    assert result.mutated is True
    reminders = [call for call in result.tool_calls if call.name == "set_reminder"]
    assert reminders, _names(result)
    reminder = reminders[0]
    assert _hhmm(reminder.arguments.get("latest_by")) == (19, 0)
    assert _hhmm(reminder.arguments.get("latest_by")) != (20, 0)
    subject = _subject(result.desk, str(reminder.arguments["subject_id"]))
    assert subject.window is not None
    assert subject.window.latest_by == time(19, 0)
    assert subject.window.latest_by != time(20, 0)
    fires = [
        row.payload.fire_at
        for row in result.desk.widgets
        if row.subject_id == subject.id and row.type == WidgetType.reminder
    ]
    assert fires and fires[0] is not None
    assert fires[0].hour == 19
    _assert_english(result)


async def test_cadence_shrink_does_not_raise_goal(live_play_en) -> None:
    result = await live_play_en("make it once a week")
    assert result.mutated is True
    push = _subject(result.desk, "push-ups")
    assert times_per_week(push.cadence) <= 1
    assert push.target is not None
    assert push.target.goal <= FOUNDING_PUSH_GOAL
    _assert_english(result)


async def test_pain_does_not_raise_goal_or_cadence(live_play_en) -> None:
    result = await live_play_en("it hurts, let's do 40")
    push = _subject(result.desk, "push-ups")
    assert push.target is not None
    assert push.target.goal <= FOUNDING_PUSH_GOAL
    assert times_per_week(push.cadence) <= FOUNDING_PUSH_WEEKLY
    for call in result.tool_calls:
        if call.name == "update_widget":
            target = call.arguments.get("target")
            if target is not None and int(target) > FOUNDING_PUSH_GOAL:
                assert call.ok is False
        elif call.name == "set_cadence":
            count = call.arguments.get("count")
            period = call.arguments.get("period", "week")
            if count is None:
                continue
            weekly = float(count) * 7 if period == "day" else float(count)
            if weekly > FOUNDING_PUSH_WEEKLY:
                assert call.ok is False
    _assert_english(result)


async def test_pain_skip_freezes_bike_without_raising_goal(live_play_en) -> None:
    result = await live_play_en("skipped today, my back hurt")
    bike = _subject(result.desk, "bike")
    assert bike.status == SubjectStatus.paused
    push = _subject(result.desk, "push-ups")
    assert push.target is not None
    assert push.target.goal <= FOUNDING_PUSH_GOAL
    for call in result.tool_calls:
        if call.name == "update_widget":
            target = call.arguments.get("target")
            if target is not None and int(target) > FOUNDING_PUSH_GOAL:
                assert call.ok is False
    _assert_english(result)


async def test_unknown_utterance_does_not_mutate(live_play_en) -> None:
    result = await live_play_en("quaxnuted probe 174")
    assert result.mutated is False


SELECTION_QUOTE_EN = "don't let the hips sag"
ORPHAN_QUOTE_EN = "running economy"


async def test_selection_lands_a_clarification_behind_a_question_mark(live_play_en) -> None:
    result = await live_play_en(
        "what does this mean?",
        TalkSelection(quote=SELECTION_QUOTE_EN, widget_id="push-ups-counter", step_id="rep-1"),
    )
    assert result.mutated is True
    fresh = [
        row
        for row in result.desk.cues
        if row.subject_id == "push-ups" and row.id not in {"push-ups-brace"}
    ]
    assert fresh, _names(result)
    assert all(row.kind == CueKind.clarification for row in fresh), [row.kind for row in fresh]
    assert all(row.surface == CueSurface.on_demand for row in fresh), [row.surface for row in fresh]
    assert any(row.quote == SELECTION_QUOTE_EN for row in fresh), [row.quote for row in fresh]
    brace = next(row for row in result.desk.cues if row.id == "push-ups-brace")
    assert brace.surface == CueSurface.do_time
    assert result.text
    _assert_english(result)


async def test_selection_with_no_binding_writes_nothing(live_play_en) -> None:
    before = founding_desk(now=NOW)
    result = await live_play_en("what does this mean?", TalkSelection(quote=ORPHAN_QUOTE_EN))
    landed = [call for call in result.tool_calls if call.name == "add_cue" and call.ok]
    assert landed == [], [call.arguments for call in landed]
    assert len(result.desk.cues) == len(before.cues)
    assert result.text
    _assert_english(result)
