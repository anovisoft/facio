"""Cadence unfolded onto dates. Count per period, not weekdays (Q26)."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, timedelta
from enum import StrEnum
from typing import Literal, Never

from pydantic import BaseModel, ConfigDict, Field, model_validator

from facio_domain.models import (
    Desk,
    Instance,
    InstanceStatus,
    Subject,
    SubjectStatus,
)

HORIZON_LEN = 7
_OPEN = frozenset({InstanceStatus.prepared, InstanceStatus.in_progress})


class SlotKind(StrEnum):
    due = "due"
    done = "done"


class Slot(BaseModel):
    """One occurrence on a date. `instance_id` is None when this is a projection."""

    model_config = ConfigDict(extra="forbid")

    subject_id: str
    date: date
    kind: SlotKind
    instance_id: str | None = None


class DayStrip(BaseModel):
    model_config = ConfigDict(extra="forbid")

    date: date
    slots: list[Slot] = Field(default_factory=list)


class Horizon(BaseModel):
    """Seven days from origin, then later dates that already have a real instance."""

    model_config = ConfigDict(extra="forbid")

    days: list[DayStrip]
    later: list[date] = Field(default_factory=list)

    @model_validator(mode="after")
    def _shape(self) -> Horizon:
        if len(self.days) != HORIZON_LEN:
            raise ValueError("horizon must be exactly 7 days")
        return self


def slot_horizon(desk: Desk, origin: date) -> Horizon:
    """Project cadence onto `[origin, origin+6]` plus later instance dates."""
    last = origin + timedelta(days=HORIZON_LEN - 1)
    day_dates = [origin + timedelta(days=offset) for offset in range(HORIZON_LEN)]
    slots_by_day: dict[date, list[Slot]] = {day: [] for day in day_dates}

    for instance in desk.instances:
        day = instance.when.date()
        if origin <= day <= last:
            slots_by_day[day].append(_real_slot(instance, day))

    by_subject = _instances_by_subject(desk.instances)
    for subject in desk.subjects:
        for slot in _projections(subject, by_subject.get(subject.id, ()), origin, last):
            slots_by_day[slot.date].append(slot)

    later = sorted(
        {
            instance.when.date()
            for instance in desk.instances
            if instance.when.date() > last
        }
    )
    return Horizon(
        days=[DayStrip(date=day, slots=slots_by_day[day]) for day in day_dates],
        later=later,
    )


def _real_slot(instance: Instance, day: date) -> Slot:
    kind = (
        SlotKind.done
        if instance.status == InstanceStatus.completed
        else SlotKind.due
    )
    return Slot(
        subject_id=instance.subject_id,
        date=day,
        kind=kind,
        instance_id=instance.id,
    )


def _instances_by_subject(instances: Sequence[Instance]) -> dict[str, list[Instance]]:
    grouped: dict[str, list[Instance]] = {}
    for instance in instances:
        grouped.setdefault(instance.subject_id, []).append(instance)
    return grouped


def _projections(
    subject: Subject,
    instances: Sequence[Instance],
    origin: date,
    last: date,
) -> list[Slot]:
    if subject.status in {SubjectStatus.retired, SubjectStatus.paused}:
        return []
    cadence = subject.cadence
    match cadence.period:
        case "none":
            return []
        case "day" | "week" as period:
            if cadence.count is None:
                return []
            count = cadence.count
        case _:
            unreachable: Never = cadence.period
            raise ValueError(unreachable)
    projected: list[Slot] = []
    for start, end in _periods_touching(origin, last, period):
        projected.extend(
            _period_projections(
                subject_id=subject.id,
                count=count,
                instances=instances,
                period_start=start,
                period_end=end,
                origin=origin,
                last=last,
            )
        )
    return projected


def _period_projections(
    *,
    subject_id: str,
    count: int,
    instances: Sequence[Instance],
    period_start: date,
    period_end: date,
    origin: date,
    last: date,
) -> list[Slot]:
    in_period = [
        instance
        for instance in instances
        if period_start <= instance.when.date() <= period_end
    ]
    completed_n = sum(
        1 for instance in in_period if instance.status == InstanceStatus.completed
    )
    open_n = sum(1 for instance in in_period if instance.status in _OPEN)
    to_project = max(0, count - completed_n - open_n)
    occupied = {instance.when.date() for instance in in_period}
    candidates: list[date] = []
    day = period_start
    while day <= period_end:
        if origin <= day <= last and day not in occupied:
            candidates.append(day)
        day += timedelta(days=1)
    return [
        Slot(subject_id=subject_id, date=day, kind=SlotKind.due, instance_id=None)
        for day in candidates[:to_project]
    ]


def _periods_touching(
    origin: date, last: date, period: Literal["day", "week"]
) -> list[tuple[date, date]]:
    spans: list[tuple[date, date]] = []
    cursor = origin
    while cursor <= last:
        start, end = _period_span(cursor, period)
        spans.append((start, end))
        cursor = end + timedelta(days=1)
    return spans


def _period_span(day: date, period: Literal["day", "week"]) -> tuple[date, date]:
    match period:
        case "day":
            return day, day
        case "week":
            start = day - timedelta(days=day.weekday())
            return start, start + timedelta(days=6)
        case _:
            unreachable: Never = period
            raise ValueError(unreachable)
