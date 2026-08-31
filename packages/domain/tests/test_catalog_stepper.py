"""Stepper as a practice, not a wizard (Q1, never-do #14).

The same four locks as the other two — rhythm, do-time cue, drift, done leaves
Today — plus the one thing the RFC says only about this type: the **tile is
not a live stepper** (04). The beats are pressed on Use, whose buttons sit at
the bottom (03 «Two fullscreens»), and nowhere else.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from facio_domain.desk import founding_desk
from facio_domain.drift import drift_card
from facio_domain.lid import lid_projection
from facio_domain.models import (
    Cadence,
    Desk,
    Instance,
    InstanceStatus,
    Subject,
    Widget,
    WidgetPayload,
    WidgetSection,
    WidgetStatus,
    WidgetType,
)
from facio_domain.morning import morning_delta
from facio_domain.runtime import (
    step_back,
    step_forward,
    stepper_beat,
    stepper_beats,
    stepper_is_last,
    stepper_position,
)
from facio_domain.tools import (
    CADENCE_REQUIRED,
    INVALID_BEATS,
    apply_tool,
    snapshot_cards,
)

NOW = datetime(2026, 8, 15, 12, 0, 0)
WARMUP = ["суставная разминка", "5 минут велотренажёра", "два подхода без веса"]


def _apply(desk: Desk, name: str, arguments: dict, *, now: datetime = NOW):
    return apply_tool(desk, name, arguments, pain=False, now=now)


def _create(desk: Desk, **overrides):
    args = {
        "type": "stepper",
        "title": "разминка",
        "subject_id": "warmup",
        "cadence": {"count": 2, "period": "week"},
        "beats": WARMUP,
    }
    args.update(overrides)
    return _apply(desk, "create_widget", args)


def _widget(desk: Desk, subject_id: str) -> Widget:
    return next(row for row in desk.widgets if row.subject_id == subject_id)


def _subject(desk: Desk, subject_id: str) -> Subject:
    return next(row for row in desk.subjects if row.id == subject_id)


# --- it lands, with beats and a rhythm ------------------------------------


def test_a_stepper_lands_with_its_beats_its_rhythm_and_its_size() -> None:
    outcome = _create(founding_desk(now=NOW))
    assert outcome.ok is True
    widget = _widget(outcome.desk, "warmup")
    assert widget.type == WidgetType.stepper
    assert stepper_beats(widget.payload) == WARMUP
    assert widget.payload.current == 0
    assert widget.tile_size == "4x2"
    assert _subject(outcome.desk, "warmup").cadence == Cadence.of(2, "week")


def test_a_stepper_on_a_new_subject_still_needs_a_rhythm() -> None:
    desk = founding_desk(now=NOW)
    outcome = _create(desk, cadence=None)
    assert outcome.ok is False
    assert outcome.error == CADENCE_REQUIRED
    assert outcome.desk is desk


@pytest.mark.parametrize(
    "beats",
    [
        pytest.param(None, id="missing"),
        pytest.param([], id="empty"),
        pytest.param("разминка, велотренажёр", id="one-string"),
        pytest.param([""], id="blank-beat"),
        pytest.param([{"text": "разминка"}], id="rows-are-not-beats"),
    ],
)
def test_a_stepper_with_no_beats_does_not_land(beats: object) -> None:
    """Without takts the type has no reason to exist — it is a tick with chrome."""
    desk = founding_desk(now=NOW)
    outcome = _create(desk, beats=beats)
    assert outcome.ok is False
    assert outcome.error == INVALID_BEATS
    assert outcome.desk is desk
    assert "warmup" not in {row.id for row in outcome.desk.subjects}


def test_only_a_stepper_takes_beats() -> None:
    desk = founding_desk(now=NOW)
    outcome = _apply(desk, "update_widget", {"widget_id": "push-ups-counter", "beats": ["раз"]})
    assert outcome.ok is False
    assert outcome.error == INVALID_BEATS
    assert outcome.desk is desk


# --- the position is one number, clamped ----------------------------------


def test_walking_the_beats_stops_at_both_ends() -> None:
    payload = WidgetPayload(beats=WARMUP, current=0)
    assert stepper_beat(payload) == WARMUP[0]
    assert stepper_is_last(payload) is False

    second = step_forward(payload)
    assert stepper_position(second) == 1
    assert stepper_beat(second) == WARMUP[1]
    # Pure: the payload handed in did not move.
    assert stepper_position(payload) == 0

    last = step_forward(step_forward(second))
    assert stepper_is_last(last) is True
    # The last beat does not roll over into the first.
    assert step_forward(last) == last

    first = step_back(step_back(step_back(last)))
    assert stepper_position(first) == 0
    assert step_back(first) == first


def test_a_position_past_the_end_reads_as_the_last_beat() -> None:
    """The sequence was rewritten shorter. Not a crash, and not a silent reset."""
    payload = WidgetPayload(beats=WARMUP, current=9)
    assert stepper_position(payload) == 2
    assert stepper_beat(payload) == WARMUP[-1]


def test_a_stepper_with_no_beats_stands_at_zero_and_does_not_move() -> None:
    payload = WidgetPayload()
    assert stepper_position(payload) == 0
    assert stepper_beat(payload) is None
    assert stepper_is_last(payload) is False
    assert step_forward(payload) == payload
    assert step_back(payload) == payload


def test_rewriting_the_beats_keeps_the_person_where_they_stand() -> None:
    created = _create(founding_desk(now=NOW))
    widget = _widget(created.desk, "warmup")
    moved = created.desk.model_copy(deep=True)
    moved.widgets = [
        row.model_copy(update={"payload": step_forward(step_forward(row.payload))})
        if row.id == widget.id
        else row
        for row in moved.widgets
    ]
    outcome = _apply(moved, "update_widget", {"widget_id": widget.id, "beats": WARMUP[:2]})
    assert outcome.ok is True
    payload = _widget(outcome.desk, "warmup").payload
    assert stepper_beats(payload) == WARMUP[:2]
    # Clamped into what now exists, never sent back to the start.
    assert stepper_position(payload) == 1


# --- complete / skip -------------------------------------------------------


def test_complete_leaves_the_sequence_on_its_last_beat() -> None:
    created = _create(founding_desk(now=NOW))
    widget = _widget(created.desk, "warmup")
    outcome = _apply(created.desk, "complete", {"widget_id": widget.id})
    done = _widget(outcome.desk, "warmup")
    assert done.status == WidgetStatus.done
    assert stepper_is_last(done.payload) is True
    instance = next(row for row in outcome.desk.instances if row.id == done.instance_id)
    assert instance.status == InstanceStatus.completed


def test_the_stepper_snapshot_is_a_picture_not_a_runtime() -> None:
    created = _create(founding_desk(now=NOW))
    widget = _widget(created.desk, "warmup")
    with_cue = _apply(
        created.desk,
        "add_cue",
        {
            "subject_id": "warmup",
            "kind": "correction",
            "text": "не тяни на холодную",
            "surface": "do-time",
        },
    )
    card = snapshot_cards(with_cue.desk, [widget.id])[0]
    assert card["line"].startswith("1 / 3")
    assert "не тяни на холодную" in card["line"]
    # No beats to press inside a chat bubble (never-do #6).
    assert "beats" not in card


# --- the cue reaches it, the drift counts it ------------------------------


def test_a_quiet_stepper_drifts_like_any_other_practice() -> None:
    subject = Subject(
        id="warmup",
        title="разминка",
        cadence=Cadence.of(2, "week"),
        instance_ids=["warmup-old"],
    )
    instances = [
        Instance(
            id="warmup-old",
            subject_id="warmup",
            when=NOW - timedelta(days=14),
            status=InstanceStatus.completed,
        )
    ]
    card = drift_card([subject], instances, NOW)
    assert card is not None
    assert card.subject_id == "warmup"


def test_the_stepper_rhythm_is_counted_in_the_morning_delta() -> None:
    subject = Subject(id="warmup", title="разминка", cadence=Cadence.of(2, "week"))
    assert morning_delta(subject, [], NOW) == 2


# --- done leaves Today -----------------------------------------------------


@pytest.mark.parametrize(
    ("when", "on_today"),
    [
        pytest.param(NOW, True, id="done-today-stays-dim"),
        pytest.param(NOW - timedelta(days=1), False, id="done-yesterday-is-gone"),
    ],
)
def test_a_finished_sequence_leaves_today_with_the_day(when: datetime, on_today: bool) -> None:
    subject = Subject(id="warmup", title="разминка", cadence=Cadence.of(2, "week"))
    widget = Widget(
        id="warmup-stepper",
        type=WidgetType.stepper,
        title="разминка",
        payload=WidgetPayload(beats=WARMUP, current=2),
        status=WidgetStatus.done,
        when=when,
        section=WidgetSection.today,
        subject_id="warmup",
        instance_id="warmup-open",
    )
    projection = lid_projection(NOW, [subject], [], [widget])
    ids = [item.widget.id for item in projection.today if item.kind == "widget"]
    assert (widget.id in ids) is on_today
