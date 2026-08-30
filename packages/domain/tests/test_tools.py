from __future__ import annotations

from datetime import datetime, time, timedelta

import pytest

from facio_domain.cues import add_cue, default_surface
from facio_domain.desk import founding_desk
from facio_domain.drift import drift_card
from facio_domain.models import (
    CueKind,
    CueOrigin,
    CueSurface,
    DriftOffer,
    SubjectStatus,
    WidgetStatus,
    WidgetType,
)
from facio_domain import tools
from facio_domain.pain import reports_pain
from facio_domain.tools import (
    CADENCE_REQUIRED,
    HOURS_REQUIRED,
    INVALID,
    INVALID_HOURS,
    INVALID_KIND,
    INVALID_MEDIA,
    INVALID_QUOTE,
    INVALID_SURFACE,
    NOT_FOUND,
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
    """Each refusal names its own field, so the next round can fix that field."""
    codes = {INVALID, INVALID_KIND, INVALID_SURFACE, INVALID_QUOTE, INVALID_MEDIA, SURFACE_REQUIRED}
    assert len(codes) == 6


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
    # The same card, as state: the number the client repaints in its own
    # language, and the cue in the person's own words.
    assert cards[0]["face"] == {"kind": "counter", "count": 28, "goal": 30}
    assert cards[0]["detail"] == "держи корпус и ягодицы"


def test_snapshot_face_carries_state_not_sentences() -> None:
    """Every phrase `line` spells out in Russian has a structural twin.

    `line` stays — a client written before this reads nothing else — but a
    client that understands `face` never sees a word the service chose.
    """
    desk = founding_desk(now=NOW)
    veg = next(row for row in desk.widgets if row.type == WidgetType.tick)
    card = snapshot_cards(desk, [veg.id])[0]
    assert card["line"] == "не сделано"
    assert card["face"] == {"kind": "tick", "done": False}

    reminder = next(row for row in desk.widgets if row.type == WidgetType.reminder)
    card = snapshot_cards(desk, [reminder.id])[0]
    face = card["face"]
    assert face["kind"] == "reminder"
    assert face["skipped"] is False
    # The door is ours to say, so it travels as a clock, not as «зал до 22».
    assert face["closes_at"] == "22:00:00"
    assert face["clock"] is not None
    assert "зал до 22" in card["line"]

    reminder.status = WidgetStatus.skipped
    card = snapshot_cards(desk, [reminder.id])[0]
    assert card["line"] == "сегодня нет"
    assert card["face"]["skipped"] is True


def test_snapshot_face_says_paused_without_saying_it() -> None:
    """The one phrase that proved the hole: «на паузе» lived in two places
    and the untranslated copy won."""
    desk = founding_desk(now=NOW)
    outcome = _apply(desk, "freeze_subject", {"subject_id": "push-ups"})
    assert outcome.ok
    widget = next(row for row in outcome.desk.widgets if row.subject_id == "push-ups")
    card = snapshot_cards(outcome.desk, [widget.id])[0]
    assert card["line"] == "на паузе"
    assert card["face"] == {"kind": "paused"}


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


def test_create_widget_refuses_a_type_with_no_runtime(monkeypatch) -> None:
    """The gate lifts **per type**, together with that type's runtime — never
    as one flag (never-do #14). Every catalog type has a runtime now, so what
    is held here is the gate itself: narrow the runnable set and the type stops
    landing, with the desk left exactly as it was.
    """
    monkeypatch.setattr(tools, "RUNNABLE_TYPES", frozenset({WidgetType.counter}))
    desk = founding_desk(now=NOW)
    subject_ids = {row.id for row in desk.subjects}
    widget_count = len(desk.widgets)
    outcome = _apply(
        desk,
        "create_widget",
        {
            "type": "checklist",
            "title": "пусто",
            "subject_id": "empty-type-new",
            "cadence": {"count": 1, "period": "week"},
            "items": ["раз"],
        },
    )
    assert outcome.ok is False
    assert outcome.mutated is False
    assert outcome.error == UNSUPPORTED_WIDGET_TYPE
    assert outcome.desk is desk
    assert len(outcome.desk.widgets) == widget_count
    assert "empty-type-new" not in {row.id for row in outcome.desk.subjects}
    assert {row.id for row in outcome.desk.subjects} == subject_ids


def test_every_catalog_type_that_ships_has_a_size_of_its_own() -> None:
    """Type owns the shape (never-do #8), out of Q18's preferred set. A type
    with no size falls into the packer's default cell and gaps the row."""
    preferred = {"4x1", "2x2", "4x2", "4x4"}
    for widget_type in tools.RUNNABLE_TYPES:
        assert tools._default_tile(widget_type) in preferred, widget_type


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


def test_add_cue_carries_step_and_media_onto_the_desk() -> None:
    """The `?` sits on a step, and a cue may carry one media item (04)."""
    desk = founding_desk(now=NOW)
    outcome = _apply(
        desk,
        "add_cue",
        {
            "id": "push-ups-hips",
            "subject_id": "push-ups",
            "step_id": "rep-1",
            "kind": "clarification",
            "text": "таз в одну линию с плечами и пятками",
            "surface": "on-demand",
            "quote": "не роняй таз",
            "media": {"kind": "link", "url": "https://example.com/hips"},
        },
    )
    assert outcome.ok
    cue = next(row for row in outcome.desk.cues if row.id == "push-ups-hips")
    assert cue.step_id == "rep-1"
    assert cue.quote == "не роняй таз"
    assert cue.media is not None
    assert cue.media.kind == "link"
    assert cue.media.url == "https://example.com/hips"
    assert cue.surface == CueSurface.on_demand
    push = next(row for row in outcome.desk.subjects if row.id == "push-ups")
    assert "push-ups-hips" in push.cue_ids


def test_add_cue_photo_media_is_the_persons_own_picture() -> None:
    desk = founding_desk(now=NOW)
    outcome = _apply(
        desk,
        "add_cue",
        {
            "id": "bike-machine",
            "subject_id": "bike",
            "kind": "clarification",
            "text": "этот тренажёр у окна",
            "surface": "on-demand",
            "media": {"kind": "photo", "ref": "local://photo/1"},
        },
    )
    assert outcome.ok
    cue = next(row for row in outcome.desk.cues if row.id == "bike-machine")
    assert cue.media is not None
    assert cue.media.kind == "photo"
    assert cue.media.ref == "local://photo/1"


def test_add_cue_refuses_more_than_one_media_item() -> None:
    """At most one: `photo` or `link`. A list is refused, not trimmed (04)."""
    desk = founding_desk(now=NOW)
    outcome = _apply(
        desk,
        "add_cue",
        {
            "subject_id": "push-ups",
            "kind": "clarification",
            "text": "две картинки",
            "surface": "on-demand",
            "media": [
                {"kind": "link", "url": "https://example.com/a"},
                {"kind": "photo", "ref": "local://photo/2"},
            ],
        },
    )
    assert not outcome.ok
    assert outcome.error == INVALID_MEDIA
    assert outcome.desk == desk


def test_add_cue_refuses_an_unknown_media_kind() -> None:
    desk = founding_desk(now=NOW)
    outcome = _apply(
        desk,
        "add_cue",
        {
            "subject_id": "push-ups",
            "kind": "clarification",
            "text": "видео из библиотеки",
            "surface": "on-demand",
            "media": {"kind": "video", "url": "https://example.com/v"},
        },
    )
    assert not outcome.ok
    assert outcome.error == INVALID_MEDIA


def test_add_cue_refuses_a_quote_that_is_an_offset() -> None:
    """`quote` is text. An anchor into a message dangles later (04)."""
    desk = founding_desk(now=NOW)
    outcome = _apply(
        desk,
        "add_cue",
        {
            "subject_id": "push-ups",
            "kind": "clarification",
            "text": "объяснение",
            "surface": "on-demand",
            "quote": {"message_id": "m1", "start": 12, "end": 24},
        },
    )
    assert not outcome.ok
    assert outcome.error == INVALID_QUOTE
    assert outcome.desk == desk


def test_add_cue_clarification_still_needs_a_surface_from_the_model() -> None:
    """The kind default lives in `add_cue`; the tool never fills it in silently."""
    desk = founding_desk(now=NOW)
    outcome = _apply(
        desk,
        "add_cue",
        {"subject_id": "push-ups", "kind": "clarification", "text": "что такое таз"},
    )
    assert not outcome.ok
    assert outcome.error == SURFACE_REQUIRED
    assert default_surface(CueKind.clarification) == CueSurface.on_demand


def test_add_cue_never_lands_on_a_subject_that_is_not_there() -> None:
    """A selection with no bound subject produces no cue — no orphans (04, 05)."""
    desk = founding_desk(now=NOW)
    outcome = _apply(
        desk,
        "add_cue",
        {
            "subject_id": "running",
            "kind": "clarification",
            "text": "беговая экономичность — сколько сил на километр",
            "surface": "on-demand",
            "quote": "беговая экономичность",
        },
    )
    assert not outcome.ok
    assert outcome.error == NOT_FOUND
    assert outcome.desk == desk
    assert outcome.desk.cues == founding_desk(now=NOW).cues


# --- Q28: a shrink said out loud is this period's answer --------------------


def _bike(desk):
    return next(row for row in desk.subjects if row.id == "bike")


def _drift_card(desk, at=NOW):
    return drift_card(desk.subjects, desk.instances, at)


def test_founding_bike_is_the_drift_card_before_anyone_speaks() -> None:
    desk = founding_desk(now=NOW)
    card = _drift_card(desk)
    assert card is not None and card.subject_id == "bike"


def test_shrinking_the_rhythm_in_talk_silences_the_card_this_period() -> None:
    """«давай велосипед раз в неделю» and no first-rung card the same morning."""
    desk = founding_desk(now=NOW)
    outcome = _apply(desk, "set_cadence", {"subject_id": "bike", "count": 1, "period": "week"})
    assert outcome.ok
    bike = _bike(outcome.desk)
    assert bike.drift_asked_at == NOW
    assert _drift_card(outcome.desk) is None


def test_a_talk_answer_leaves_the_rung_where_it_was() -> None:
    desk = founding_desk(now=NOW)
    outcome = _apply(desk, "set_cadence", {"subject_id": "bike", "count": 1, "period": "week"})
    bike = _bike(outcome.desk)
    assert bike.drift_asks_made == 0
    assert bike.drift_retire_refusals == 0
    later = _drift_card(outcome.desk, NOW + timedelta(days=8))
    assert later is not None
    assert later.offer == DriftOffer.move_to_today


def test_raising_the_rhythm_in_talk_does_not_buy_quiet() -> None:
    desk = founding_desk(now=NOW)
    outcome = _apply(desk, "set_cadence", {"subject_id": "bike", "count": 5, "period": "week"})
    assert outcome.ok
    assert _bike(outcome.desk).drift_asked_at is None
    assert _drift_card(outcome.desk) is not None


def test_shrink_retire_and_freeze_all_spend_the_ask() -> None:
    for name, args in (
        ("shrink_subject", {"subject_id": "bike"}),
        ("retire_subject", {"subject_id": "bike"}),
        ("freeze_subject", {"subject_id": "bike"}),
    ):
        outcome = _apply(founding_desk(now=NOW), name, args)
        assert outcome.ok, name
        assert _bike(outcome.desk).drift_asked_at == NOW, name


def test_thaw_keeps_the_stamp_the_freeze_left() -> None:
    """After «верни велосипед» the period counts from the talk, not last year."""
    frozen = _apply(founding_desk(now=NOW), "freeze_subject", {"subject_id": "bike"}).desk
    thawed = _apply(frozen, "thaw_subject", {"subject_id": "bike"}).desk
    bike = _bike(thawed)
    assert bike.status == SubjectStatus.active
    assert bike.drift_asked_at == NOW
    assert _drift_card(thawed, NOW + timedelta(days=1)) is None
    assert _drift_card(thawed, NOW + timedelta(days=8)) is not None


def test_moving_one_instance_is_not_an_answer() -> None:
    """`move_to_date` moves a card, not the promise: the question still stands."""
    desk = founding_desk(now=NOW)
    outcome = _apply(
        desk, "move_to_date", {"widget_id": "bike-reminder", "when": "2026-08-15T19:00:00"}
    )
    assert outcome.ok
    assert _bike(outcome.desk).drift_asked_at is None
    assert _drift_card(outcome.desk) is not None


def test_a_talk_answer_touches_only_the_subject_it_was_about() -> None:
    desk = founding_desk(now=NOW)
    outcome = _apply(desk, "shrink_subject", {"subject_id": "bike"})
    others = [row for row in outcome.desk.subjects if row.id != "bike"]
    assert all(row.drift_asked_at is None for row in others)
    assert all(row.drift_asks_made == 0 for row in others)


def test_set_reminder_takes_all_the_hours_that_were_named() -> None:
    """The Upwork reply: seven hours, one window, nothing invented (Q34)."""
    desk = founding_desk(now=NOW)
    created = _apply(
        desk,
        "create_widget",
        {
            "type": "tick",
            "title": "проверить upwork",
            "subject_id": "upwork",
            "cadence": {"count": 7, "period": "day"},
        },
    )
    outcome = _apply(
        created.desk,
        "set_reminder",
        {
            "subject_id": "upwork",
            "hours": ["10:00", "12:00", "15:00", "16:30", "18:00", "21:00", "22:00"],
        },
    )
    assert outcome.ok
    window = next(row.window for row in outcome.desk.subjects if row.id == "upwork")
    assert window is not None
    assert [hour.strftime("%H:%M") for hour in window.hours] == [
        "10:00",
        "12:00",
        "15:00",
        "16:30",
        "18:00",
        "21:00",
        "22:00",
    ]
    assert outcome.data["hours"] == [hour.isoformat() for hour in window.hours]
    # The old wire still reads: the first hour, where one hour used to sit.
    assert outcome.data["latest_by"] == "10:00:00"
    fire = next(
        row.payload.fire_at
        for row in outcome.desk.widgets
        if row.subject_id == "upwork" and row.type == WidgetType.reminder
    )
    assert fire is not None
    assert fire.strftime("%H:%M") == "10:00"


def test_set_reminder_hour_by_hour_ends_up_in_the_same_window() -> None:
    """Seven calls of one hour, or one call of seven — the desk is the same."""
    desk = founding_desk(now=NOW)
    created = _apply(
        desk,
        "create_widget",
        {
            "type": "tick",
            "title": "проверить upwork",
            "subject_id": "upwork",
            "cadence": {"count": 7, "period": "day"},
        },
    )
    running = created.desk
    for clock in ["10:00", "12:00", "15:00", "16:30", "18:00", "21:00", "22:00"]:
        outcome = _apply(running, "set_reminder", {"subject_id": "upwork", "latest_by": clock})
        assert outcome.ok
        running = outcome.desk
    window = next(row.window for row in running.subjects if row.id == "upwork")
    assert window is not None
    assert len(window.hours) == 7
    assert window.latest_by == time(10, 0)


def test_set_reminder_does_not_overwrite_the_hour_that_stands() -> None:
    desk = founding_desk(now=NOW)
    first = _apply(desk, "set_reminder", {"subject_id": "bike", "latest_by": "21:00"})
    window = next(row.window for row in first.desk.subjects if row.id == "bike")
    # 19:00 was already on the practice; 21:00 joins it, it does not replace it.
    assert window is not None
    assert window.hours == [time(19, 0), time(21, 0)]


def test_set_reminder_is_idempotent_on_the_same_hour() -> None:
    desk = founding_desk(now=NOW)
    once = _apply(desk, "set_reminder", {"subject_id": "bike", "latest_by": "19:00"})
    twice = _apply(once.desk, "set_reminder", {"subject_id": "bike", "latest_by": "19:00"})
    window = next(row.window for row in twice.desk.subjects if row.id == "bike")
    assert window is not None
    assert window.hours == [time(19, 0)]


def test_removing_an_hour_is_said_out_loud() -> None:
    desk = founding_desk(now=NOW)
    added = _apply(desk, "set_reminder", {"subject_id": "bike", "hours": ["07:00", "21:00"]})
    dropped = _apply(added.desk, "set_reminder", {"subject_id": "bike", "remove_hours": ["07:00"]})
    assert dropped.ok
    window = next(row.window for row in dropped.desk.subjects if row.id == "bike")
    assert window is not None
    assert window.hours == [time(19, 0), time(21, 0)]


def test_removing_the_last_hour_is_refused_by_name() -> None:
    desk = founding_desk(now=NOW)
    outcome = _apply(desk, "set_reminder", {"subject_id": "bike", "remove_hours": ["19:00"]})
    assert not outcome.ok
    assert outcome.error == HOURS_REQUIRED
    window = next(row.window for row in outcome.desk.subjects if row.id == "bike")
    assert window is not None
    assert window.hours == [time(19, 0)]


def test_hours_that_are_not_clocks_are_refused_by_name() -> None:
    desk = founding_desk(now=NOW)
    outcome = _apply(desk, "set_reminder", {"subject_id": "bike", "hours": [10, 12]})
    assert not outcome.ok
    assert outcome.error == INVALID_HOURS


def test_the_door_still_leaves_every_stated_hour_alone() -> None:
    """Q34 does not touch the door: 22:00 → 19:00, and a named hour wins."""
    desk = founding_desk(now=NOW)
    named = _apply(desk, "set_reminder", {"subject_id": "bike", "hours": ["10:00", "18:00"]})
    outcome = _apply(named.desk, "set_reminder", {"subject_id": "bike", "closes_at": "23:00"})
    assert outcome.ok
    window = next(row.window for row in outcome.desk.subjects if row.id == "bike")
    assert window is not None
    assert window.hours == [time(10, 0), time(18, 0), time(19, 0)]
    assert window.closes_at == time(23, 0)
