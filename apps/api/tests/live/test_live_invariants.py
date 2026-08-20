"""Desk invariants against a live vendor. Not golden tool sequences or verbatim text."""

from __future__ import annotations

from datetime import time

import pytest

from facio_domain.models import CueSurface, Desk, WidgetType
from facio_domain.tools import times_per_week

from facio_api.talk.schemas import TalkTurnResponse

pytestmark = pytest.mark.live

SEED_BRACE = "держи корпус и ягодицы"
FOUNDING_BRACE = "brace the core and the glutes"
FOUNDING_IDS = {"bike", "push-ups", "vegetables"}
FOUNDING_PUSH_WEEKLY = 3.0
FOUNDING_PUSH_GOAL = 30


def _names(result: TalkTurnResponse) -> list[str]:
    return [call.name for call in result.tool_calls]


def _subject(desk: Desk, subject_id: str):
    return next(row for row in desk.subjects if row.id == subject_id)


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


async def test_method_4_to_30_lands_current_and_cue(live_play) -> None:
    result = await live_play("могу 4, хочу 30 подряд, как?")
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
    assert method_cues
    assert result.snapshots
    assert result.text


async def test_gym_no_clock_creates_counter_without_reminder(live_play) -> None:
    result = await live_play("запиши зал")
    names = _names(result)
    assert result.mutated is True
    assert "set_reminder" not in names
    create = next(
        call
        for call in result.tool_calls
        if call.name == "create_widget"
        and call.arguments.get("type") == "counter"
        and call.arguments.get("subject_id") not in FOUNDING_IDS
    )
    subject_id = create.arguments["subject_id"]
    reminders = [
        row for row in result.desk.widgets if row.subject_id == subject_id and row.type == WidgetType.reminder
    ]
    assert reminders == []
    bike = _subject(result.desk, "bike")
    assert bike.window is not None
    assert bike.window.latest_by == time(19, 0)
    assert any(row.id == "bike-reminder" for row in result.desk.widgets)


async def test_miss_skip_does_not_hang_a_clock(live_play) -> None:
    result = await live_play("сегодня не сходил")
    names = _names(result)
    assert result.mutated is True
    assert any(call.name == "skip" and call.ok for call in result.tool_calls)
    assert "set_reminder" not in names
    bike = _subject(result.desk, "bike")
    assert bike.window is not None
    assert bike.window.latest_by == time(19, 0)


async def test_remind_at_19_uses_stated_hour(live_play) -> None:
    result = await live_play("напомни в 19, в 21 я уже сплю")
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
    assert any("сп" in row.text.casefold() for row in timing)
    assert "add_cue" in names


async def test_gym_until_22_is_arithmetic(live_play) -> None:
    result = await live_play("зал до 22")
    assert result.mutated is True
    reminder = next(
        call
        for call in result.tool_calls
        if call.name == "set_reminder" and _hhmm(call.arguments.get("closes_at")) == (22, 0)
    )
    assert _hhmm(reminder.arguments.get("latest_by")) != (19, 0)
    bike = _subject(result.desk, "bike")
    assert bike.window is not None
    assert bike.window.closes_at == time(22, 0)
    assert bike.window.latest_by == time(19, 0)


NAMED_HOUR_AND_DOOR = (
    "Хочу пойти в зал, но постоянно забываю про него и к 23 он уже закрывается. "
    "Напоминай мне о том что мне нужно пойти в зал в 19 часов"
)


async def test_named_hour_beats_closing_formula(live_play) -> None:
    result = await live_play(NAMED_HOUR_AND_DOOR)
    assert result.mutated is True
    reminder = next(call for call in result.tool_calls if call.name == "set_reminder")
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


async def test_cadence_shrink_does_not_raise_goal(live_play) -> None:
    result = await live_play("давай раз в неделю")
    assert result.mutated is True
    push = _subject(result.desk, "push-ups")
    assert times_per_week(push.cadence) <= 1
    assert push.target is not None
    assert push.target.goal <= FOUNDING_PUSH_GOAL


async def test_pain_does_not_raise_goal_or_cadence(live_play) -> None:
    result = await live_play("больно, давай 40")
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


async def test_unknown_utterance_does_not_mutate(live_play) -> None:
    result = await live_play("квэкснутый зонд 174")
    assert result.mutated is False
