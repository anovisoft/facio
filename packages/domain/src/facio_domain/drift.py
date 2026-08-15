"""Derived drift. Never stored as a field or a score."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Never

from facio_domain.models import (
    Cadence,
    DriftAskState,
    DriftCard,
    DriftOffer,
    Instance,
    InstanceStatus,
    Subject,
    SubjectStatus,
)

# Q27: one full cadence period of silence, with zero done instances in the tail.
# Weekly → 8 days. Daily-ish (count=1, period=day) → 3 days.
SILENCE_DAYS_WEEK = 8
SILENCE_DAYS_DAY = 3

_ACTIVITY = frozenset({InstanceStatus.completed, InstanceStatus.in_progress})


def silence_threshold(cadence: Cadence) -> int | None:
    """Days of silence that count as one missed period. None = cannot drift."""
    if cadence.is_none:
        return None
    match cadence.period:
        case "week":
            return SILENCE_DAYS_WEEK
        case "day":
            return SILENCE_DAYS_DAY
        case "none":
            return None
        case _:
            unreachable: Never = cadence.period
            raise ValueError(unreachable)


def last_activity_at(
    subject: Subject, instances: Sequence[Instance]
) -> datetime | None:
    own = [
        item
        for item in instances
        if item.subject_id == subject.id and item.status in _ACTIVITY
    ]
    if not own:
        return None
    return max(item.when for item in own)


def silence_days(
    subject: Subject, instances: Sequence[Instance], now: datetime
) -> int | None:
    """Calendar days since last completed or in-progress instance.

    None if there is no activity — a subject that has never started is not
    drifting (empty today without a commitment, not a missed period).
    """
    last = last_activity_at(subject, instances)
    if last is None:
        return None
    return (now.date() - last.date()).days


def is_drifting(
    subject: Subject, instances: Sequence[Instance], now: datetime
) -> bool:
    """True when one full cadence period has passed with zero done instances.

    cadence none with no instances is a finished thing, not drift.
    Missing a weekday at 3×/week is not failure; v0 drift is silence (Q27),
    not an under-count of a partially filled period.
    """
    if subject.status == SubjectStatus.retired:
        return False
    threshold = silence_threshold(subject.cadence)
    if threshold is None:
        return False
    days = silence_days(subject, instances, now)
    if days is None:
        return False
    return days >= threshold


def next_drift_offer(asks_made: int, retire_refusals: int) -> DriftOffer:
    """Q28 shrink ladder. Volume does not rise. After two retire refusals: stop.

    The function only names the next offer. Removing cadence after `stop`
    happens outside.
    """
    if retire_refusals >= 2:
        return DriftOffer.stop
    if asks_made <= 0:
        return DriftOffer.move_to_today
    if asks_made == 1:
        return DriftOffer.once_a_week
    return DriftOffer.retire


def drift_card(
    subjects: Sequence[Subject],
    instances: Sequence[Instance],
    now: datetime,
    histories: Mapping[str, DriftAskState] | None = None,
) -> DriftCard | None:
    """At most one drift card. If several subjects drift, the oldest silence wins."""
    states = histories or {}
    drifting: list[tuple[int, str, Subject]] = []
    for subject in subjects:
        if not is_drifting(subject, instances, now):
            continue
        days = silence_days(subject, instances, now)
        if days is None:
            continue
        drifting.append((days, subject.id, subject))
    if not drifting:
        return None
    days, _sid, subject = max(drifting, key=lambda row: (row[0], row[1]))
    state = states.get(subject.id, DriftAskState())
    return DriftCard(
        subject_id=subject.id,
        silent_days=days,
        offer=next_drift_offer(state.asks_made, state.retire_refusals),
    )
