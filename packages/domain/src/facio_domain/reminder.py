"""Deterministic reminder timing from a subject's window. No LLM."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

from facio_domain.models import Subject, Window

# Founding bike case: gym shuts at 22:00 → fire at 19:00.
CLOSING_LEAD = timedelta(hours=3)


def window_from_closing(closes_at: time) -> Window:
    """Derive a window: latest_by is closing minus 3 hours."""
    latest = (datetime.combine(date.min, closes_at) - CLOSING_LEAD).time()
    return Window(hours=[latest], closes_at=closes_at)


def reminder_fire_at(subject: Subject, window: Window, on_date: date) -> datetime:
    """When the reminder first fires on `on_date`. The window sets the hour."""
    del subject
    return reminder_fire_times(window, on_date)[0]


def reminder_fire_times(window: Window, on_date: date) -> list[datetime]:
    """Every hour of the window, laid on one date, in order.

    A window with one hour gives one time — the shape it always had. Several
    stated hours give several, and each of them is an alarm of its own (Q34).
    """
    return [datetime.combine(on_date, hour) for hour in window.hours]
