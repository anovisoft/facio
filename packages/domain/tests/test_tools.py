from __future__ import annotations

from datetime import datetime, time

import pytest

from facio_domain.cues import add_cue
from facio_domain.desk import founding_desk
from facio_domain.models import CueOrigin, CueSurface, SubjectStatus, WidgetStatus, WidgetType
from facio_domain.pain import reports_pain
from facio_domain.tools import (
    CADENCE_REQUIRED,
    INVALID,
    INVALID_KIND,
    INVALID_SURFACE,
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


def test_add_cue_with_a_surface_value_in_kind_names_the_kind_field() -> None:
    """The live hole: kind="timing". Name the field; do not turn it into a correction."""
    desk = founding_desk(now=NOW)
    outcome = _apply(
        desk,
        "add_cue",
        {"subject_id": "bike", "kind": "timing", "text": "в 21 сплю", "surface": "timing"},
    )
    assert not outcome.ok
    assert outcome.error == INVALID_KIND
    assert outcome.desk == desk
    assert not [row for row in outcome.desk.cues if row.text == "в 21 сплю"]


def test_add_cue_with_an_unknown_surface_names_the_surface_field() -> None:
    desk = founding_desk(now=NOW)
    outcome = _apply(
        desk,
        "add_cue",
        {"subject_id": "push-ups", "kind": "correction", "text": "держи корпус", "surface": "rep-one"},
    )
    assert not outcome.ok
    assert outcome.error == INVALID_SURFACE
    assert outcome.desk == desk


def test_add_cue_empty_required_argument_stays_bare_invalid() -> None:
    desk = founding_desk(now=NOW)
    outcome = _apply(
        desk,
        "add_cue",
        {"subject_id": "push-ups", "kind": "correction", "text": "  ", "surface": "do-time"},
    )
    assert not outcome.ok
    assert outcome.error == INVALID


def test_add_cue_refusal_codes_are_distinct() -> None:
    assert len({INVALID, INVALID_KIND, INVALID_SURFACE, SURFACE_REQUIRED}) == 4


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


def test_pain_does_not_block_freeze() -> None:
    desk = founding_desk(now=NOW)
    bike = next(row for row in desk.subjects if row.id == "bike")
    cadence = bike.cadence
    target = bike.target
    instance_ids = list(bike.instance_ids)
    cue_ids = list(bike.cue_ids)
    outcome = _apply(desk, "freeze_subject", {"subject_id": "bike"}, pain=True)
    assert outcome.ok
    frozen = next(row for row in outcome.desk.subjects if row.id == "bike")
    assert frozen.status == SubjectStatus.paused
    assert frozen.paused_at == NOW
    assert frozen.cadence == cadence
    assert frozen.target == target
    assert frozen.instance_ids == instance_ids
    assert frozen.cue_ids == cue_ids
    widgets = [row for row in outcome.desk.widgets if row.subject_id == "bike"]
    assert any(row.id == "bike-reminder" for row in widgets)


def test_freeze_retired_is_invalid() -> None:
    desk = founding_desk(now=NOW)
    retired = _apply(desk, "retire_subject", {"subject_id": "bike"})
    outcome = _apply(retired.desk, "freeze_subject", {"subject_id": "bike"})
    assert not outcome.ok
    assert outcome.error == INVALID
    assert outcome.desk is retired.desk
    bike = next(row for row in outcome.desk.subjects if row.id == "bike")
    assert bike.status == SubjectStatus.retired
    assert bike.paused_at is None


def test_thaw_restores_active_and_clears_paused_at() -> None:
    desk = founding_desk(now=NOW)
    frozen = _apply(desk, "freeze_subject", {"subject_id": "bike"})
    outcome = _apply(frozen.desk, "thaw_subject", {"subject_id": "bike"})
    assert outcome.ok
    bike = next(row for row in outcome.desk.subjects if row.id == "bike")
    assert bike.status == SubjectStatus.active
    assert bike.paused_at is None


def test_thaw_unskips_the_subjects_widgets() -> None:
    desk = founding_desk(now=NOW)
    skipped = _apply(desk, "skip", {"widget_id": "bike-reminder"})
    frozen = _apply(skipped.desk, "freeze_subject", {"subject_id": "bike"})
    outcome = _apply(frozen.desk, "thaw_subject", {"subject_id": "bike"})
    assert outcome.ok
    widget = next(row for row in outcome.desk.widgets if row.id == "bike-reminder")
    assert widget.status == WidgetStatus.ready


def test_thaw_without_pause_is_invalid() -> None:
    desk = founding_desk(now=NOW)
    outcome = _apply(desk, "thaw_subject", {"subject_id": "bike"})
    assert not outcome.ok
    assert outcome.error == INVALID
    assert outcome.desk is desk
    bike = next(row for row in outcome.desk.subjects if row.id == "bike")
    assert bike.status == SubjectStatus.active


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


def test_create_widget_on_a_new_subject_without_cadence_is_refused() -> None:
    """A practice with no rhythm is a planner line (06 #14). Refuse, do not guess."""
    desk = founding_desk(now=NOW)
    subject_ids = {row.id for row in desk.subjects}
    widget_count = len(desk.widgets)
    instance_count = len(desk.instances)
    outcome = _apply(
        desk,
        "create_widget",
        {"type": "counter", "title": "зал", "subject_id": "gym-no-cadence"},
    )
    assert outcome.ok is False
    assert outcome.mutated is False
    assert outcome.error == CADENCE_REQUIRED
    assert outcome.desk is desk
    assert {row.id for row in outcome.desk.subjects} == subject_ids
    assert len(outcome.desk.widgets) == widget_count
    assert len(outcome.desk.instances) == instance_count


@pytest.mark.parametrize(
    "cadence",
    [
        pytest.param({}, id="empty-object"),
        pytest.param({"count": 2}, id="count-without-period"),
        pytest.param("2 раза в неделю", id="prose-instead-of-a-rhythm"),
        pytest.param(None, id="explicit-null"),
    ],
)
def test_create_widget_half_named_cadence_is_still_refused(cadence: object) -> None:
    """Half a rhythm is not a rhythm. The law never fills in the missing half."""
    desk = founding_desk(now=NOW)
    outcome = _apply(
        desk,
        "create_widget",
        {"type": "counter", "title": "зал", "subject_id": "gym-half", "cadence": cadence},
    )
    assert outcome.ok is False
    assert outcome.mutated is False
    assert outcome.error == CADENCE_REQUIRED
    assert "gym-half" not in {row.id for row in outcome.desk.subjects}


def test_create_widget_writes_the_named_cadence() -> None:
    desk = founding_desk(now=NOW)
    outcome = _apply(
        desk,
        "create_widget",
        {
            "type": "counter",
            "title": "зал",
            "subject_id": "gym-twice",
            "cadence": {"count": 2, "period": "week"},
        },
    )
    assert outcome.ok
    assert outcome.mutated is True
    subject = next(row for row in outcome.desk.subjects if row.id == "gym-twice")
    assert subject.cadence.count == 2
    assert subject.cadence.period == "week"
    assert times_per_week(subject.cadence) == 2


def test_create_widget_accepts_an_explicit_none_cadence() -> None:
    """A one-off is legal — `none` said out loud is not the same as `none` inherited."""
    desk = founding_desk(now=NOW)
    outcome = _apply(
        desk,
        "create_widget",
        {
            "type": "tick",
            "title": "поменять права",
            "subject_id": "licence-once",
            "cadence": {"period": "none"},
        },
    )
    assert outcome.ok
    subject = next(row for row in outcome.desk.subjects if row.id == "licence-once")
    assert subject.cadence.period == "none"
    assert subject.cadence.count is None


def test_create_widget_on_an_existing_subject_needs_no_cadence() -> None:
    """The rhythm already stands; a second widget does not ask for it again."""
    desk = founding_desk(now=NOW)
    before = next(row.cadence for row in desk.subjects if row.id == "push-ups")
    outcome = _apply(
        desk,
        "create_widget",
        {"type": "tick", "title": "отжимания", "subject_id": "push-ups"},
    )
    assert outcome.ok
    assert outcome.mutated is True
    after = next(row.cadence for row in outcome.desk.subjects if row.id == "push-ups")
    assert after == before


def test_create_widget_bad_cadence_period_is_invalid_not_a_guess() -> None:
    desk = founding_desk(now=NOW)
    outcome = _apply(
        desk,
        "create_widget",
        {
            "type": "counter",
            "title": "зал",
            "subject_id": "gym-bad-period",
            "cadence": {"count": 2, "period": "month"},
        },
    )
    assert outcome.ok is False
    assert outcome.error == INVALID
    assert "gym-bad-period" not in {row.id for row in outcome.desk.subjects}


def test_create_widget_counter_on_new_subject_does_not_spawn_reminder() -> None:
    desk = founding_desk(now=NOW)
    outcome = _apply(
        desk,
        "create_widget",
        {
            "type": "counter",
            "title": "зал",
            "subject_id": "gym-counter-new",
            "target": 30,
            "cadence": {"count": 2, "period": "week"},
        },
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
        {
            "type": "tick",
            "title": "овощи",
            "subject_id": "veg-tick-new",
            "cadence": {"count": 1, "period": "day"},
        },
    )
    assert outcome.ok
    widgets = [row for row in outcome.desk.widgets if row.subject_id == "veg-tick-new"]
    assert len(widgets) == 1
    assert widgets[0].type == WidgetType.tick
    assert not any(row.type == WidgetType.reminder for row in widgets)


def test_update_widget_count_writes_target_current() -> None:
    desk = founding_desk(now=NOW)
    outcome = _apply(desk, "update_widget", {"widget_id": "push-ups-counter", "count": 4})
    assert outcome.ok
    subject = next(row for row in outcome.desk.subjects if row.id == "push-ups")
    assert subject.target is not None
    assert subject.target.current == 4
    assert subject.target.goal == 30
    widget = next(row for row in outcome.desk.widgets if row.id == "push-ups-counter")
    assert widget.payload.count == 4


def test_set_reminder_creates_widget_when_subject_has_none() -> None:
    desk = founding_desk(now=NOW)
    assert not any(row.type == WidgetType.reminder and row.subject_id == "vegetables" for row in desk.widgets)
    outcome = _apply(desk, "set_reminder", {"subject_id": "vegetables", "latest_by": "19:00"})
    assert outcome.ok
    reminders = [
        row for row in outcome.desk.widgets if row.subject_id == "vegetables" and row.type == WidgetType.reminder
    ]
    assert len(reminders) == 1
    assert reminders[0].tile_size == "4x2"
    assert reminders[0].payload.fire_at is not None
    assert reminders[0].payload.fire_at.hour == 19
    bike_reminders = [
        row for row in outcome.desk.widgets if row.subject_id == "bike" and row.type == WidgetType.reminder
    ]
    assert len(bike_reminders) == 1


def test_create_widget_reminder_is_allowed() -> None:
    desk = founding_desk(now=NOW)
    outcome = _apply(
        desk,
        "create_widget",
        {
            "type": "reminder",
            "title": "час",
            "subject_id": "nap-reminder-new",
            "cadence": {"count": 1, "period": "day"},
        },
    )
    assert outcome.ok
    widgets = [row for row in outcome.desk.widgets if row.subject_id == "nap-reminder-new"]
    assert len(widgets) == 1
    assert widgets[0].type == WidgetType.reminder


def test_set_reminder_stated_hour_beats_closing_formula() -> None:
    desk = founding_desk(now=NOW)
    outcome = _apply(
        desk,
        "set_reminder",
        {"subject_id": "bike", "latest_by": "19:00", "closes_at": "23:00"},
    )
    assert outcome.ok
    window = next(row.window for row in outcome.desk.subjects if row.id == "bike")
    assert window is not None
    assert window.latest_by == time(19, 0)
    assert window.closes_at == time(23, 0)
    fire = next(row.payload.fire_at for row in outcome.desk.widgets if row.id == "bike-reminder")
    assert fire is not None
    assert fire.hour == 19
    assert fire.hour != 20


def test_set_reminder_closing_only_keeps_named_hour() -> None:
    desk = founding_desk(now=NOW)
    named = _apply(desk, "set_reminder", {"subject_id": "bike", "latest_by": "18:00"})
    outcome = _apply(named.desk, "set_reminder", {"subject_id": "bike", "closes_at": "23:00"})
    assert outcome.ok
    window = next(row.window for row in outcome.desk.subjects if row.id == "bike")
    assert window is not None
    assert window.latest_by == time(18, 0)
    assert window.closes_at == time(23, 0)
    fire = next(row.payload.fire_at for row in outcome.desk.widgets if row.id == "bike-reminder")
    assert fire is not None
    assert fire.hour == 18
    cards = snapshot_cards(outcome.desk, outcome.snapshot_widget_ids)
    assert cards[0]["line"] == "18:00 · зал до 23"


def test_set_reminder_closing_only_without_hour_uses_formula() -> None:
    desk = founding_desk(now=NOW)
    created = _apply(
        desk,
        "create_widget",
        {
            "type": "counter",
            "title": "зал",
            "subject_id": "gym",
            "cadence": {"count": 2, "period": "week"},
        },
    )
    outcome = _apply(created.desk, "set_reminder", {"subject_id": "gym", "closes_at": "22:00"})
    assert outcome.ok
    window = next(row.window for row in outcome.desk.subjects if row.id == "gym")
    assert window is not None
    assert window.latest_by == time(19, 0)
    assert window.closes_at == time(22, 0)


def test_counter_without_a_goal_draws_no_goal() -> None:
    """«0 / 0» is a target nobody named. No goal — just the number."""
    desk = founding_desk(now=NOW)
    outcome = _apply(
        desk,
        "create_widget",
        {
            "type": "counter",
            "title": "зал",
            "subject_id": "gym-line",
            "cadence": {"count": 2, "period": "week"},
        },
    )
    assert outcome.ok
    cards = snapshot_cards(outcome.desk, outcome.snapshot_widget_ids)
    assert cards[0]["line"] == "0"
    assert "/" not in cards[0]["line"]


def test_counter_with_a_goal_still_draws_the_pair() -> None:
    desk = founding_desk(now=NOW)
    cards = snapshot_cards(desk, ["push-ups-counter"])
    assert cards[0]["line"].startswith("28 / 30")


def test_freeze_snapshot_says_paused() -> None:
    desk = founding_desk(now=NOW)
    outcome = _apply(desk, "freeze_subject", {"subject_id": "bike"})
    cards = snapshot_cards(outcome.desk, outcome.snapshot_widget_ids)
    assert cards
    assert cards[0]["line"] == "на паузе"


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
    bike_reminders = [
        row for row in outcome.desk.widgets if row.subject_id == "bike" and row.type == WidgetType.reminder
    ]
    assert len(bike_reminders) == 1


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
