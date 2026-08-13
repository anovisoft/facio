"""Physical-day gate: cycle anchor + local calendar date → unlocked day.

See docs/next/04-model.md §4 and docs/next/09-continuity.md decision E.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Literal

from app.errors import ValidationAppError


def parse_local_date(value: str | None) -> date:
    """Parse client-supplied ``YYYY-MM-DD``; fallback to UTC today."""
    if value is None or not value.strip():
        return datetime.now(UTC).date()
    try:
        return date.fromisoformat(value.strip())
    except ValueError as exc:
        raise ValidationAppError(
            f"Invalid local_date (expected YYYY-MM-DD): {value!r}"
        ) from exc


def resolve_cycle_anchor(
    *, committed_at: datetime, first_step_when: Literal["today", "tomorrow"]
) -> date:
    """Cycle anchor at commit: commit date, +1 day when starting tomorrow."""
    anchor = committed_at.date()
    if first_step_when == "tomorrow":
        anchor += timedelta(days=1)
    return anchor


def unlocked_day_index(
    *,
    anchor: date | None,
    horizon_days: int,
    local_today: date,
) -> int:
    """Physical unlock ceiling for execute.

    - Missing anchor (legacy pre-Slice-4): fully unlocked.
    - ``local_today < anchor`` (e.g. committed with first_step_when=tomorrow):
      ``-1`` — nothing executable yet; days remain preview-locked.
    - Else: ``min(local_today - anchor, horizon_days - 1)``.
    """
    horizon = max(1, horizon_days)
    if anchor is None:
        return horizon - 1
    delta = (local_today - anchor).days
    if delta < 0:
        return -1
    return min(delta, horizon - 1)


def day_unlock_date(anchor: date | None, day_offset: int | None) -> date | None:
    """Calendar date a given day_offset becomes unlocked, or None if unknown."""
    if anchor is None or day_offset is None:
        return None
    return anchor + timedelta(days=day_offset)


def is_day_locked(day_offset: int | None, unlocked: int) -> bool:
    """True when the action's day is not yet executable (``unlocked`` may be -1)."""
    return day_offset is not None and day_offset > unlocked
