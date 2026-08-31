"""Timer as a practice, not a stopwatch (Q1, never-do #14).

Same four locks as the checklist: it lands with a rhythm, the do-time cue
reaches it, silence past a cadence period is drift, and a finished sitting
leaves Today with the day. Plus the one thing a timer owns — elapsed seconds
are **derived** from the moment the run began, never stored ticking.
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
    pause_timer,
    reset_timer,
    start_timer,
    timer_elapsed,
    timer_is_done,
    timer_is_running,
    timer_remaining,
)
from facio_domain.tools import (
    CADENCE_REQUIRED,
    INVALID_SECONDS,
    apply_tool,
    snapshot_cards,
)

NOW = datetime(2026, 8, 15, 12, 0, 0)
TEN_MINUTES = 600


def _apply(desk: Desk, name: str, arguments: dict, *, now: datetime = NOW):
    return apply_tool(desk, name, arguments, pain=False, now=now)


def _create(desk: Desk, **overrides):
    args = {
        "type": "timer",
        "title": "медитация",
        "subject_id": "meditation",
        "cadence": {"count": 1, "period": "day"},
        "seconds": TEN_MINUTES,
    }
    args.update(overrides)
    return _apply(desk, "create_widget", args)


def _widget(desk: Desk, subject_id: str) -> Widget:
    return next(row for row in desk.widgets if row.subject_id == subject_id)


def _subject(desk: Desk, subject_id: str) -> Subject:
    return next(row for row in desk.subjects if row.id == subject_id)


# --- it lands, with a length and a rhythm ---------------------------------


def test_a_timer_lands_with_its_length_its_rhythm_and_its_size() -> None:
    outcome = _create(founding_desk(now=NOW))
    assert outcome.ok is True
    widget = _widget(outcome.desk, "meditation")
    assert widget.type == WidgetType.timer
    assert widget.payload.seconds == TEN_MINUTES
    # A fresh timer is standing still: nothing banked, no run going.
    assert widget.payload.elapsed == 0
    assert widget.payload.started_at is None
    assert widget.tile_size == "2x2"
    assert _subject(outcome.desk, "meditation").cadence == Cadence.of(1, "day")


def test_a_timer_on_a_new_subject_still_needs_a_rhythm() -> None:
    desk = founding_desk(now=NOW)
    outcome = _create(desk, cadence=None)
    assert outcome.ok is False
    assert outcome.error == CADENCE_REQUIRED
    assert outcome.desk is desk


@pytest.mark.parametrize(
    "seconds",
    [
        pytest.param(None, id="missing"),
        pytest.param(0, id="zero"),
        pytest.param(-60, id="negative"),
        pytest.param("десять минут", id="words"),
        pytest.param(True, id="a-bool-is-not-a-length"),
    ],
)
def test_a_timer_with_no_length_does_not_land(seconds: object) -> None:
    """A timer without a length is a stopwatch, and a stopwatch has no do-time."""
    desk = founding_desk(now=NOW)
    outcome = _create(desk, seconds=seconds)
    assert outcome.ok is False
    assert outcome.error == INVALID_SECONDS
    assert outcome.desk is desk
    assert "meditation" not in {row.id for row in outcome.desk.subjects}


def test_only_a_timer_takes_a_length() -> None:
    desk = founding_desk(now=NOW)
    outcome = _apply(desk, "update_widget", {"widget_id": "push-ups-counter", "seconds": 60})
    assert outcome.ok is False
    assert outcome.error == INVALID_SECONDS
    assert outcome.desk is desk


# --- elapsed is arithmetic -------------------------------------------------


def test_elapsed_comes_from_the_moment_the_run_began() -> None:
    payload = WidgetPayload(seconds=TEN_MINUTES, elapsed=0)
    assert timer_is_running(payload) is False
    assert timer_elapsed(payload, NOW) == 0

    running = start_timer(payload, NOW)
    assert timer_is_running(running) is True
    assert running.started_at == NOW
    # No stored ticking number anywhere: the clock does the counting.
    assert running.elapsed == 0
    assert timer_elapsed(running, NOW + timedelta(seconds=90)) == 90
    assert timer_remaining(running, NOW + timedelta(seconds=90)) == TEN_MINUTES - 90


def test_pausing_banks_the_run_and_resuming_keeps_it() -> None:
    running = start_timer(WidgetPayload(seconds=TEN_MINUTES), NOW)
    paused = pause_timer(running, NOW + timedelta(seconds=120))
    assert paused.started_at is None
    assert paused.elapsed == 120
    # The banked seconds do not keep running while it is stopped.
    assert timer_elapsed(paused, NOW + timedelta(hours=3)) == 120

    resumed = start_timer(paused, NOW + timedelta(hours=3))
    assert timer_elapsed(resumed, NOW + timedelta(hours=3, seconds=60)) == 180


def test_starting_a_running_timer_does_not_restart_it() -> None:
    """Pressing start twice must not throw away the minutes already spent."""
    running = start_timer(WidgetPayload(seconds=TEN_MINUTES), NOW)
    again = start_timer(running, NOW + timedelta(seconds=200))
    assert again == running
    assert timer_elapsed(again, NOW + timedelta(seconds=200)) == 200


def test_pausing_a_stopped_timer_changes_nothing() -> None:
    payload = WidgetPayload(seconds=TEN_MINUTES, elapsed=45)
    assert pause_timer(payload, NOW) == payload


def test_a_clock_that_moved_back_is_not_a_debt() -> None:
    payload = WidgetPayload(seconds=TEN_MINUTES, started_at=NOW + timedelta(minutes=5))
    assert timer_elapsed(payload, NOW) == 0
    assert timer_remaining(payload, NOW) == TEN_MINUTES


def test_a_timer_with_no_length_is_never_done() -> None:
    running = start_timer(WidgetPayload(), NOW)
    assert timer_is_done(running, NOW + timedelta(days=1)) is False


def test_the_length_survives_a_reset() -> None:
    spent = pause_timer(start_timer(WidgetPayload(seconds=TEN_MINUTES), NOW), NOW + timedelta(seconds=300))
    fresh = reset_timer(spent)
    assert fresh.seconds == TEN_MINUTES
    assert fresh.elapsed == 0
    assert fresh.started_at is None


def test_the_named_length_is_spent() -> None:
    running = start_timer(WidgetPayload(seconds=TEN_MINUTES), NOW)
    assert timer_is_done(running, NOW + timedelta(seconds=599)) is False
    assert timer_is_done(running, NOW + timedelta(seconds=600)) is True
    assert timer_remaining(running, NOW + timedelta(seconds=900)) == 0


# --- complete / skip -------------------------------------------------------


def test_complete_stops_the_run_and_banks_it() -> None:
    """A finished sitting is not a running one: the tile must not keep
    counting past a closed case."""
    created = _create(founding_desk(now=NOW))
    widget = _widget(created.desk, "meditation")
    # Starting is a finger on the device, not a tool the mouth can call, so the
    # run is set up here the way the client would leave it on the desk.
    desk = created.desk.model_copy(deep=True)
    desk.widgets = [
        row.model_copy(update={"payload": start_timer(row.payload, NOW)}) if row.id == widget.id else row
        for row in desk.widgets
    ]
    outcome = _apply(desk, "complete", {"widget_id": widget.id}, now=NOW + timedelta(seconds=600))
    done = _widget(outcome.desk, "meditation")
    assert done.status == WidgetStatus.done
    assert done.payload.started_at is None
    assert done.payload.elapsed == 600
    assert timer_elapsed(done.payload, NOW + timedelta(hours=2)) == 600
    instance = next(row for row in outcome.desk.instances if row.id == done.instance_id)
    assert instance.status == InstanceStatus.completed


def test_the_timer_snapshot_is_a_picture_not_a_runtime() -> None:
    created = _create(founding_desk(now=NOW))
    widget = _widget(created.desk, "meditation")
    with_cue = _apply(
        created.desk,
        "add_cue",
        {
            "subject_id": "meditation",
            "kind": "correction",
            "text": "сядь ровно, дыши носом",
            "surface": "do-time",
        },
    )
    card = snapshot_cards(with_cue.desk, [widget.id])[0]
    assert card["line"].startswith("10:00")
    assert "сядь ровно" in card["line"]
    assert "started_at" not in card
    assert "elapsed" not in card


# --- the cue reaches it, the drift counts it ------------------------------


def test_a_quiet_timer_drifts_like_any_other_practice() -> None:
    subject = Subject(
        id="meditation",
        title="медитация",
        cadence=Cadence.of(1, "day"),
        instance_ids=["meditation-old"],
    )
    instances = [
        Instance(
            id="meditation-old",
            subject_id="meditation",
            when=NOW - timedelta(days=5),
            status=InstanceStatus.completed,
        )
    ]
    card = drift_card([subject], instances, NOW)
    assert card is not None
    assert card.subject_id == "meditation"


def test_the_timer_rhythm_is_counted_in_the_morning_delta() -> None:
    subject = Subject(id="meditation", title="медитация", cadence=Cadence.of(1, "day"))
    assert morning_delta(subject, [], NOW) == 1


# --- done leaves Today -----------------------------------------------------


@pytest.mark.parametrize(
    ("when", "on_today"),
    [
        pytest.param(NOW, True, id="done-today-stays-dim"),
        pytest.param(NOW - timedelta(days=1), False, id="done-yesterday-is-gone"),
    ],
)
def test_a_finished_sitting_leaves_today_with_the_day(when: datetime, on_today: bool) -> None:
    subject = Subject(id="meditation", title="медитация", cadence=Cadence.of(1, "day"))
    widget = Widget(
        id="meditation-timer",
        type=WidgetType.timer,
        title="медитация",
        payload=WidgetPayload(seconds=TEN_MINUTES, elapsed=TEN_MINUTES),
        status=WidgetStatus.done,
        when=when,
        section=WidgetSection.today,
        subject_id="meditation",
        instance_id="meditation-open",
    )
    projection = lid_projection(NOW, [subject], [], [widget])
    ids = [item.widget.id for item in projection.today if item.kind == "widget"]
    assert (widget.id in ids) is on_today
