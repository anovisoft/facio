from __future__ import annotations

from datetime import datetime, time

import pytest

from facio_domain.cues import add_cue
from facio_domain.desk import founding_desk
from facio_domain.models import CueOrigin, CueSurface, WidgetType
from facio_domain.pain import reports_pain
from facio_domain.tools import (
    PAIN_FORBIDS_RAISE,
    SURFACE_REQUIRED,
    UNSUPPORTED_WIDGET_TYPE,
    apply_tool,
    snapshot_cards,
    times_per_week,
)


NOW = datetime(2026, 8, 15, 12, 0, 0)
ORIGIN = CueOrigin(chat_id="chat-1", message_id="msg-1")


def _apply(desk, name: str, arguments: dict, *, pain: bool = False):
    return apply_tool(desk, name, arguments, pain=pain, now=NOW, origin=ORIGIN)


def test_add_cue_without_surface_is_rejected() -> None:
    desk = founding_desk(now=NOW)
    outcome = _apply(
        desk,
        "add_cue",
        {"subject_id": "push-ups", "kind": "correction", "text": "держи корпус"},
    )
    assert not outcome.ok
    assert outcome.error == SURFACE_REQUIRED
    assert outcome.desk == desk


def test_add_cue_lands_on_push_ups_do_time() -> None:
    desk = founding_desk(now=NOW)
    outcome = _apply(
        desk,
        "add_cue",
        {
            "id": "push-ups-brace-talk",
            "subject_id": "push-ups",
            "kind": "correction",
            "text": "держи корпус и ягодицы",
            "surface": "do-time",
        },
    )
    assert outcome.ok
    assert outcome.mutated
    cue = next(row for row in outcome.desk.cues if row.id == "push-ups-brace-talk")
    assert cue.subject_id == "push-ups"
    assert cue.surface == CueSurface.do_time
    assert cue.origin == ORIGIN
    assert "push-ups-brace-talk" in next(
        row.cue_ids for row in outcome.desk.subjects if row.id == "push-ups"
    )
    cards = snapshot_cards(outcome.desk, outcome.snapshot_widget_ids)
    assert cards[0]["widget_id"] == "push-ups-counter"
    assert "держи корпус" in cards[0]["line"]


def test_pain_blocks_target_raise_and_keeps_goal() -> None:
    desk = founding_desk(now=NOW)
    assert reports_pain("больно, давай 40")
    outcome = _apply(
        desk,
        "update_widget",
        {"widget_id": "push-ups-counter", "target": 40},
        pain=True,
    )
    assert not outcome.ok
    assert outcome.error == PAIN_FORBIDS_RAISE
    goal = next(row.target.goal for row in desk.subjects if row.id == "push-ups")
    assert goal == 30
    assert next(row.payload.target for row in desk.widgets if row.id == "push-ups-counter") == 30


def test_pain_allows_add_cue_and_lower_target() -> None:
    desk = founding_desk(now=NOW)
    cue = _apply(
        desk,
        "add_cue",
        {
            "subject_id": "push-ups",
            "kind": "correction",
            "text": "держи корпус и ягодицы",
            "surface": "do-time",
        },
        pain=True,
    )
    assert cue.ok
    lower = _apply(
        cue.desk,
        "update_widget",
        {"widget_id": "push-ups-counter", "target": 20},
        pain=True,
    )
    assert lower.ok
    assert next(row.target.goal for row in lower.desk.subjects if row.id == "push-ups") == 20


def test_pain_blocks_cadence_raise() -> None:
    desk = founding_desk(now=NOW)
    outcome = _apply(
        desk,
        "set_cadence",
        {"subject_id": "push-ups", "count": 5, "period": "week"},
        pain=True,
    )
    assert outcome.error == PAIN_FORBIDS_RAISE
    cadence = next(row.cadence for row in desk.subjects if row.id == "push-ups")
    assert times_per_week(cadence) == 3


@pytest.mark.parametrize("widget_type", ["checklist", "timer", "stepper"])
def test_create_widget_empty_type_is_rejected(widget_type: str) -> None:
    desk = founding_desk(now=NOW)
    subject_ids = {row.id for row in desk.subjects}
    widget_count = len(desk.widgets)
    outcome = _apply(
        desk,
        "create_widget",
        {"type": widget_type, "title": "пусто", "subject_id": "empty-type-new"},
    )
    assert outcome.ok is False
    assert outcome.mutated is False
    assert outcome.error == UNSUPPORTED_WIDGET_TYPE
    assert outcome.desk is desk
    assert len(outcome.desk.widgets) == widget_count
    assert "empty-type-new" not in {row.id for row in outcome.desk.subjects}
    assert {row.id for row in outcome.desk.subjects} == subject_ids


def test_create_widget_counter_on_new_subject_does_not_spawn_reminder() -> None:
    desk = founding_desk(now=NOW)
    outcome = _apply(
        desk,
        "create_widget",
        {"type": "counter", "title": "зал", "subject_id": "gym-counter-new", "target": 30},
    )
    assert outcome.ok
    widgets = [row for row in outcome.desk.widgets if row.subject_id == "gym-counter-new"]
    assert len(widgets) == 1
    assert widgets[0].type == WidgetType.counter
    assert not any(row.type == WidgetType.reminder for row in widgets)


def test_create_widget_tick_on_new_subject_does_not_spawn_reminder() -> None:
    desk = founding_desk(now=NOW)
    outcome = _apply(
        desk,
        "create_widget",
        {"type": "tick", "title": "овощи", "subject_id": "veg-tick-new"},
    )
    assert outcome.ok
    widgets = [row for row in outcome.desk.widgets if row.subject_id == "veg-tick-new"]
    assert len(widgets) == 1
    assert widgets[0].type == WidgetType.tick
    assert not any(row.type == WidgetType.reminder for row in widgets)


def test_create_widget_reminder_is_allowed() -> None:
    desk = founding_desk(now=NOW)
    outcome = _apply(
        desk,
        "create_widget",
        {"type": "reminder", "title": "час", "subject_id": "nap-reminder-new"},
    )
    assert outcome.ok
    widgets = [row for row in outcome.desk.widgets if row.subject_id == "nap-reminder-new"]
    assert len(widgets) == 1
    assert widgets[0].type == WidgetType.reminder


def test_set_reminder_from_closing_is_arithmetic() -> None:
    desk = founding_desk(now=NOW)
    outcome = _apply(desk, "set_reminder", {"subject_id": "bike", "closes_at": "22:00"})
    assert outcome.ok
    window = next(row.window for row in outcome.desk.subjects if row.id == "bike")
    assert window is not None
    assert window.latest_by == time(19, 0)
    assert window.closes_at == time(22, 0)
    fire = next(row.payload.fire_at for row in outcome.desk.widgets if row.id == "bike-reminder")
    assert fire is not None
    assert fire.hour == 19


def test_orphan_cue_is_rejected() -> None:
    desk = founding_desk(now=NOW)
    outcome = _apply(
        desk,
        "add_cue",
        {
            "subject_id": "no-such",
            "kind": "correction",
            "text": "ghost",
            "surface": "do-time",
        },
    )
    assert not outcome.ok
    assert outcome.error == "not_found"


def test_domain_add_cue_still_defaults_surface() -> None:
    cue = add_cue(id="x", subject_id="push-ups", kind="correction", text="brace")
    assert cue.surface == CueSurface.do_time
