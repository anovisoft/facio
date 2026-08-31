"""The morning card: delta or drift, at most one, never both (Q6, P8).

Delta is the calm half. It is arithmetic on the rhythm the person set — what
this period promised minus what actually got done — computed on the morning of
the day. It carries no offer and no chips: a practice that is merely behind
gets a sentence, not a ladder. Drift is the loud half and it lives in
`drift.py`; when both are true the drift card wins, because a missed period is
the failure this product exists for and the delta is only its quieter cousin.

Nothing here invents a chore (never-do #15). Every number comes from a cadence
the person named and instances they closed themselves.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timedelta
from typing import Never

from facio_domain.drift import is_drifting, last_activity_at
from facio_domain.models import (
    Cadence,
    DeltaCard,
    Instance,
    InstanceStatus,
    Subject,
    SubjectStatus,
    Widget,
    WidgetStatus,
)

_DONE = frozenset({InstanceStatus.completed})
_LIVE_TODAY = frozenset({WidgetStatus.ready, WidgetStatus.running})


def period_days(cadence: Cadence) -> int | None:
    """Length of one cadence period in days. None when there is no rhythm."""
    if cadence.is_none:
        return None
    match cadence.period:
        case "week":
            return 7
        case "day":
            return 1
        case "none":
            return None
        case _:
            unreachable: Never = cadence.period
            raise ValueError(unreachable)


def promised(cadence: Cadence) -> int:
    """How many times this period was promised. No rhythm promises nothing."""
    if cadence.is_none:
        return 0
    return cadence.count or 0


def done_in_period(
    subject: Subject, instances: Sequence[Instance], now: datetime
) -> int:
    """Completed instances inside the trailing cadence period ending today.

    A trailing window, not a calendar week: cadence is a count per period, not
    fixed weekdays (Q26), so Monday must not reset anybody's arithmetic.
    """
    days = period_days(subject.cadence)
    if days is None:
        return 0
    start = (now - timedelta(days=days - 1)).date()
    return sum(
        1
        for item in instances
        if item.subject_id == subject.id
        and item.status in _DONE
        and start <= item.when.date() <= now.date()
    )


def morning_delta(
    subject: Subject, instances: Sequence[Instance], now: datetime
) -> int:
    """Promised minus done for this period, floored at zero.

    Doing more than promised is not a debt, so the delta never goes negative
    and never turns into a score to beat (P7).
    """
    return max(0, promised(subject.cadence) - done_in_period(subject, instances, now))


def _has_live_tile_today(subject: Subject, widgets: Sequence[Widget]) -> bool:
    """Is this practice already sitting on Today, waiting for a finger?

    If it is, the tile *is* the delta made physical, and a card repeating it
    would be a second inventory of the same commitment (P10). The morning line
    is for a practice that promised something this period and has nothing on
    Today to do it with.
    """
    return any(
        widget.subject_id == subject.id
        and widget.section.value == "today"
        and widget.status in _LIVE_TODAY
        for widget in widgets
    )


def delta_card(
    subjects: Sequence[Subject],
    instances: Sequence[Instance],
    widgets: Sequence[Widget],
    now: datetime,
) -> DeltaCard | None:
    """At most one delta card: the biggest shortfall, oldest id on a tie.

    Skips a drifting subject on purpose — that one gets the drift card, and
    saying the same thing twice in one morning would be the nagging P8 rules
    out. Skips paused and retired: a frozen practice owes nothing.

    A practice that has never run once owes nothing either. Drift already
    refuses to fire on a subject with no activity, and the delta follows the
    same line: a rhythm nobody has started yet is a plan, and turning it into
    a debt on day one is inventing a chore (never-do #15).
    """
    rows: list[tuple[int, str, Subject]] = []
    for subject in subjects:
        if subject.status in {SubjectStatus.retired, SubjectStatus.paused}:
            continue
        if last_activity_at(subject, instances) is None:
            continue
        if is_drifting(subject, instances, now):
            continue
        if _has_live_tile_today(subject, widgets):
            continue
        remaining = morning_delta(subject, instances, now)
        if remaining <= 0:
            continue
        rows.append((remaining, subject.id, subject))
    if not rows:
        return None
    remaining, _sid, subject = max(rows, key=lambda row: (row[0], row[1]))
    return DeltaCard(
        subject_id=subject.id,
        promised=promised(subject.cadence),
        done=done_in_period(subject, instances, now),
        remaining=remaining,
    )
