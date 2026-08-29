"""Derived drift and the shrink ladder. Never stored as a field or a score.

The law owns three decisions the model is never allowed to make (never-do AI
#10): whether a subject is drifting, which rung of the ladder is next, and
whether there is a right to speak at all. The model may word one line.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Never

from facio_domain.models import (
    Cadence,
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

# Q28: two refusals of the offer to retire and the product stops asking.
RETIRE_REFUSALS_TO_SILENCE = 2

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


def ask_period_days(cadence: Cadence) -> int | None:
    """How long the ladder waits between two asks about the same subject.

    Q28 says at most once per cadence period, same object, same volume. The
    gap is the same arithmetic the drift threshold uses, so a weekly practice
    hears about it at most every eight days and a daily-ish one every three.
    Not a separate knob: two numbers here would drift apart.
    """
    return silence_threshold(cadence)


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
    if subject.status in {SubjectStatus.retired, SubjectStatus.paused}:
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

    Rung 1 move it to today, rung 2 once a week instead, rung 3 retire it.
    Every rung is less commitment than the one before; none of them is a
    bigger number and none of them is «try harder» (never-do #21).
    """
    if retire_refusals >= RETIRE_REFUSALS_TO_SILENCE:
        return DriftOffer.stop
    if asks_made <= 0:
        return DriftOffer.move_to_today
    if asks_made == 1:
        return DriftOffer.once_a_week
    return DriftOffer.retire


def next_offer(subject: Subject) -> DriftOffer:
    """The rung this subject is standing on, read off the subject itself."""
    return next_drift_offer(subject.drift_asks_made, subject.drift_retire_refusals)


def can_ask_now(subject: Subject, now: datetime) -> bool:
    """The right to speak: `stop` is silence forever, otherwise one per period.

    Ignoring a card does not escalate inside a period and does not silence the
    product either — after a full period the same question may be asked again,
    same object, same volume (P8).
    """
    if next_offer(subject) == DriftOffer.stop:
        return False
    asked_at = subject.drift_asked_at
    if asked_at is None:
        return True
    period = ask_period_days(subject.cadence)
    if period is None:
        return False
    return (now.date() - asked_at.date()).days >= period


def answer_drift(subject: Subject, offer: DriftOffer, now: datetime) -> Subject:
    """What the answer does to the practice. Down the ladder, never up.

    `move_to_today` touches no subject field beyond the ask bookkeeping — the
    widgets move, the commitment does not change. `once_a_week` is the same
    write `set_cadence` / `shrink_subject` makes. `retire` keeps every
    instance and every cue (04): nothing is deleted as punishment.
    """
    updates: dict[str, object] = {
        "drift_asks_made": subject.drift_asks_made + 1,
        "drift_asked_at": now,
    }
    match offer:
        case DriftOffer.move_to_today:
            pass
        case DriftOffer.once_a_week:
            updates["cadence"] = Cadence.of(1, "week")
            updates["status"] = SubjectStatus.shrunk
        case DriftOffer.retire:
            updates["status"] = SubjectStatus.retired
        case DriftOffer.stop:
            return subject
        case _:
            unreachable: Never = offer
            raise ValueError(unreachable)
    return subject.model_copy(update=updates)


def refuse_drift(subject: Subject, offer: DriftOffer, now: datetime) -> Subject:
    """«Not now». Costs one rung; refusing to retire twice ends the asking.

    On the second refusal of `retire` the cadence goes away and the subject
    stays exactly where it was — alive in Deeds, instances and cues intact
    (Q28). Without a cadence it can no longer drift, which is the point: the
    product stops speaking instead of getting louder.
    """
    asks_made = subject.drift_asks_made + 1
    refusals = subject.drift_retire_refusals
    if offer == DriftOffer.retire:
        refusals += 1
    updates: dict[str, object] = {
        "drift_asks_made": asks_made,
        "drift_retire_refusals": refusals,
        "drift_asked_at": now,
    }
    if refusals >= RETIRE_REFUSALS_TO_SILENCE:
        updates["cadence"] = Cadence.none()
    return subject.model_copy(update=updates)


def drift_card(
    subjects: Sequence[Subject],
    instances: Sequence[Instance],
    now: datetime,
) -> DriftCard | None:
    """At most one drift card. If several subjects drift, the oldest silence wins.

    Subjects that may not be asked right now — already asked this period, or
    silenced after two refusals — are filtered out first, so a quiet one does
    not block a louder failure behind it (Q27 still yields one card).
    """
    drifting: list[tuple[int, str, Subject]] = []
    for subject in subjects:
        if not is_drifting(subject, instances, now):
            continue
        if not can_ask_now(subject, now):
            continue
        days = silence_days(subject, instances, now)
        if days is None:
            continue
        drifting.append((days, subject.id, subject))
    if not drifting:
        return None
    days, _sid, subject = max(drifting, key=lambda row: (row[0], row[1]))
    return DriftCard(
        subject_id=subject.id,
        silent_days=days,
        offer=next_offer(subject),
    )
