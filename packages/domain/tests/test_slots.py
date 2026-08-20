from __future__ import annotations

from datetime import date, datetime, timedelta

from facio_domain.desk import founding_desk
from facio_domain.models import (
    Cadence,
    Desk,
    Instance,
    InstanceStatus,
    Subject,
    SubjectStatus,
    Window,
)
from facio_domain.slots import Horizon, Slot, SlotKind, slot_horizon

NOW = datetime(2026, 8, 15, 12, 0, 0)
ORIGIN = NOW.date()  # Saturday


def _desk(subjects: list[Subject], instances: list[Instance] | None = None) -> Desk:
    return Desk(subjects=subjects, cues=[], instances=instances or [], widgets=[])


def _subject(
    subject_id: str,
    cadence: Cadence,
    *,
    status: SubjectStatus = SubjectStatus.active,
    window: Window | None = None,
) -> Subject:
    return Subject(
        id=subject_id,
        title=subject_id,
        cadence=cadence,
        status=status,
        window=window,
    )


def _instance(
    instance_id: str,
    subject_id: str,
    when: datetime,
    status: InstanceStatus = InstanceStatus.prepared,
) -> Instance:
    return Instance(id=instance_id, subject_id=subject_id, when=when, status=status)


def _slots(horizon: Horizon, subject_id: str) -> list[Slot]:
    return [
        slot
        for strip in horizon.days
        for slot in strip.slots
        if slot.subject_id == subject_id
    ]


def test_horizon_is_seven_consecutive_days_from_origin() -> None:
    desk = founding_desk(now=NOW)
    horizon = slot_horizon(desk, ORIGIN)
    dates = [strip.date for strip in horizon.days]
    assert len(dates) == 7
    assert dates[0] == ORIGIN
    assert dates == [ORIGIN + timedelta(days=offset) for offset in range(7)]


def test_founding_vegetables_today_real_then_projected_due() -> None:
    desk = founding_desk(now=NOW)
    horizon = slot_horizon(desk, ORIGIN)
    vegetables = _slots(horizon, "vegetables")
    today = [slot for slot in vegetables if slot.date == ORIGIN]
    assert len(today) == 1
    assert today[0].kind == SlotKind.due
    assert today[0].instance_id == "vegetables-open"
    later_days = [slot for slot in vegetables if slot.date > ORIGIN]
    assert [slot.date for slot in later_days] == [
        ORIGIN + timedelta(days=offset) for offset in range(1, 7)
    ]
    assert all(slot.kind == SlotKind.due for slot in later_days)
    assert all(slot.instance_id is None for slot in later_days)


def test_founding_push_ups_do_not_mark_weekdays_before_origin_missed() -> None:
    desk = founding_desk(now=NOW)
    horizon = slot_horizon(desk, ORIGIN)
    week_monday = date(2026, 8, 10)
    day_dates = [strip.date for strip in horizon.days]
    assert week_monday not in day_dates
    assert date(2026, 8, 11) not in day_dates
    today = [slot for slot in _slots(horizon, "push-ups") if slot.date == ORIGIN]
    assert any(
        slot.instance_id == "push-ups-open" and slot.kind == SlotKind.due
        for slot in today
    )


def test_weekly_projections_fill_remaining_days_not_past_monday_tuesday() -> None:
    origin = date(2026, 8, 12)  # Wednesday
    desk = _desk([_subject("push-ups", Cadence.of(3, "week"))])
    horizon = slot_horizon(desk, origin)
    projected = [slot.date for slot in _slots(horizon, "push-ups")]
    this_sunday = date(2026, 8, 16)
    this_week = [day for day in projected if day <= this_sunday]
    assert this_week == [date(2026, 8, 12), date(2026, 8, 13), date(2026, 8, 14)]
    assert all(slot.instance_id is None for slot in _slots(horizon, "push-ups"))
    day_dates = [strip.date for strip in horizon.days]
    assert date(2026, 8, 10) not in day_dates
    assert date(2026, 8, 11) not in day_dates
    assert date(2026, 8, 10) not in projected
    assert date(2026, 8, 11) not in projected


def test_completed_before_origin_is_neither_in_days_nor_later() -> None:
    origin = date(2026, 8, 12)  # Wednesday
    tuesday = datetime(2026, 8, 11, 9, 0, 0)
    desk = _desk(
        [_subject("push-ups", Cadence.of(3, "week"))],
        [
            _instance(
                "done-tue",
                "push-ups",
                tuesday,
                InstanceStatus.completed,
            )
        ],
    )
    horizon = slot_horizon(desk, origin)
    day_dates = [strip.date for strip in horizon.days]
    assert tuesday.date() not in day_dates
    assert tuesday.date() not in horizon.later
    assert all(slot.instance_id != "done-tue" for slot in _slots(horizon, "push-ups"))


def test_instance_ten_days_out_is_later_not_in_days() -> None:
    desk = founding_desk(now=NOW)
    far = ORIGIN + timedelta(days=10)
    extra = _instance(
        "later-set",
        "push-ups",
        datetime.combine(far, NOW.time()),
        InstanceStatus.prepared,
    )
    desk = desk.model_copy(update={"instances": [*desk.instances, extra]})
    horizon = slot_horizon(desk, ORIGIN)
    day_dates = [strip.date for strip in horizon.days]
    assert far in horizon.later
    assert far not in day_dates
    assert all(slot.instance_id != "later-set" for slot in _slots(horizon, "push-ups"))


def test_cadence_none_without_instances_has_no_projections() -> None:
    origin = date(2026, 8, 12)
    desk = _desk([_subject("gift", Cadence.none())])
    horizon = slot_horizon(desk, origin)
    assert _slots(horizon, "gift") == []
    assert horizon.later == []


def test_bike_window_does_not_move_slot_to_another_day() -> None:
    desk = founding_desk(now=NOW)
    horizon = slot_horizon(desk, ORIGIN)
    real = [
        slot
        for slot in _slots(horizon, "bike")
        if slot.instance_id == "bike-open"
    ]
    assert len(real) == 1
    assert real[0].date == ORIGIN
    assert real[0].kind == SlotKind.due


def test_weekly_leftover_does_not_spill_into_next_week() -> None:
    origin = date(2026, 8, 15)  # Saturday
    desk = _desk([_subject("push-ups", Cadence.of(3, "week"))])
    horizon = slot_horizon(desk, origin)
    projected = [slot.date for slot in _slots(horizon, "push-ups")]
    # This ISO week has only Sat/Sun left; the third count is dropped, not a Monday debt.
    assert date(2026, 8, 15) in projected
    assert date(2026, 8, 16) in projected
    # Next week has its own 3 — Mon/Tue/Wed — not a fourth day from leftover.
    assert projected == [
        date(2026, 8, 15),
        date(2026, 8, 16),
        date(2026, 8, 17),
        date(2026, 8, 18),
        date(2026, 8, 19),
    ]
    assert date(2026, 8, 20) not in projected


def test_retired_subject_shows_real_instance_without_projections() -> None:
    origin = date(2026, 8, 12)
    desk = _desk(
        [_subject("old", Cadence.of(3, "week"), status=SubjectStatus.retired)],
        [_instance("old-open", "old", datetime(2026, 8, 12, 8, 0, 0))],
    )
    horizon = slot_horizon(desk, origin)
    slots = _slots(horizon, "old")
    assert len(slots) == 1
    assert slots[0].instance_id == "old-open"
    assert slots[0].kind == SlotKind.due
    assert all(slot.instance_id is not None for slot in slots)


def test_paused_subject_shows_real_instance_without_projections() -> None:
    origin = date(2026, 8, 12)
    desk = _desk(
        [_subject("bike", Cadence.of(2, "week"), status=SubjectStatus.paused)],
        [_instance("bike-open", "bike", datetime(2026, 8, 12, 8, 0, 0))],
    )
    horizon = slot_horizon(desk, origin)
    slots = _slots(horizon, "bike")
    assert len(slots) == 1
    assert slots[0].instance_id == "bike-open"
    assert slots[0].kind == SlotKind.due
    assert all(slot.instance_id is not None for slot in slots)


def test_two_instances_same_subject_same_day_both_emitted() -> None:
    origin = date(2026, 8, 12)
    when = datetime(2026, 8, 12, 8, 0, 0)
    desk = _desk(
        [_subject("push-ups", Cadence.of(3, "week"))],
        [
            _instance("a", "push-ups", when, InstanceStatus.completed),
            _instance("b", "push-ups", when.replace(hour=18), InstanceStatus.prepared),
        ],
    )
    horizon = slot_horizon(desk, origin)
    today = [slot for slot in _slots(horizon, "push-ups") if slot.date == origin]
    real = [slot for slot in today if slot.instance_id is not None]
    assert {slot.instance_id for slot in real} == {"a", "b"}
    assert {slot.kind for slot in real} == {SlotKind.done, SlotKind.due}
