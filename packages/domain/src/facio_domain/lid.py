"""Lid projection. The lid is a view, not a table."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Never

from facio_domain.drift import drift_card
from facio_domain.groups import group_face, group_key, says_every_hour
from facio_domain.models import (
    DeltaTodayItem,
    DriftTodayItem,
    Instance,
    LidProjection,
    RankBand,
    Subject,
    SubjectStatus,
    Widget,
    WidgetSection,
    WidgetStatus,
    WidgetTodayItem,
    WidgetType,
)
from facio_domain.morning import delta_card

_HIDDEN_TODAY = frozenset(
    {
        WidgetStatus.skipped,
        WidgetStatus.archived,
        WidgetStatus.snoozed,
    }
)


def _without_paused(
    subjects: Sequence[Subject], widgets: Sequence[Widget]
) -> list[Widget]:
    paused = {subject.id for subject in subjects if subject.status == SubjectStatus.paused}
    return [widget for widget in widgets if widget.subject_id not in paused]


def reminder_shadowed_by_group(
    subject: Subject,
    widgets: Sequence[Widget],
    instances: Sequence[Instance],
    now: datetime,
) -> bool:
    """Whether this subject's reminder tile is a second copy of its group tile.

    One practice, one promise, one tile. When today's group of this subject
    already carries the hours the window states, the reminder tile repeats it
    word for word — `15:30` large, `18:00 22:00` small — and the lid stops being
    a view of what is due now (P10).

    Only today's group counts, and only a group of more than one: a practice
    that promises once a day is never stamped, so a desk written before Q34
    draws exactly as it always did.
    """
    face = group_face(group_key(subject.id, now.date()), widgets, instances, now)
    if face is None or face.total < 2:
        return False
    return says_every_hour(face, subject.window)


def _without_repeated_reminders(
    now: datetime,
    subjects: Sequence[Subject],
    instances: Sequence[Instance],
    widgets: Sequence[Widget],
) -> list[Widget]:
    """Drop the reminder tile of a subject whose group already speaks its hours.

    A drawing rule and nothing else. The widget stays on the desk, keeps its
    status and keeps ringing: alarms are read off the desk snapshot, never off
    this projection, so a tile that is not drawn is not an alarm that was
    cancelled.
    """
    silent = {
        subject.id
        for subject in subjects
        if reminder_shadowed_by_group(subject, widgets, instances, now)
    }
    if not silent:
        return list(widgets)
    return [
        widget
        for widget in widgets
        if widget.type != WidgetType.reminder or widget.subject_id not in silent
    ]


def _band_index(band: RankBand) -> int:
    match band:
        case RankBand.in_progress:
            return 0
        case RankBand.overdue:
            return 1
        case RankBand.unanswered_morning:
            return 2
        case RankBand.drift_card:
            return 3
        case RankBand.soon_by_time:
            return 4
        case RankBand.today_incomplete:
            return 5
        case RankBand.today_done:
            return 6
        case _:
            unreachable: Never = band
            raise ValueError(unreachable)


def _is_done_today(widget: Widget, now: datetime) -> bool:
    if widget.status != WidgetStatus.done or widget.when is None:
        return False
    return widget.when.date() == now.date()


def widget_rank_band(widget: Widget, now: datetime) -> RankBand:
    """Rank v0 band for a Today widget. Morning is a hole unless a card exists."""
    if widget.status == WidgetStatus.done:
        return RankBand.today_done
    if widget.status == WidgetStatus.running:
        return RankBand.in_progress
    if widget.when is not None and widget.when < now:
        return RankBand.overdue
    if (
        widget.when is not None
        and widget.when.date() == now.date()
        and widget.when > now
    ):
        return RankBand.soon_by_time
    return RankBand.today_incomplete


def _sort_key(
    item: WidgetTodayItem | DriftTodayItem | DeltaTodayItem, now: datetime
) -> tuple:
    if isinstance(item, DriftTodayItem):
        return (_band_index(RankBand.drift_card), datetime.min, item.drift_card.subject_id)
    if isinstance(item, DeltaTodayItem):
        return (
            _band_index(RankBand.unanswered_morning),
            datetime.min,
            item.delta_card.subject_id,
        )
    when = item.widget.when or now
    return (_band_index(item.band), when, item.widget.id)


def belongs_to_a_closed_day(widget: Widget, now: datetime) -> bool:
    """Whether this widget belongs to a day that is over (R19).

    A `group_id` names a subject **and a date**, so a widget carrying
    yesterday's id is one of yesterday's checks. Once the day rolls over, today
    has its own group, and drawing the old one as well would put two tiles of
    one practice on the lid (R17) and quietly hand yesterday's misses to today —
    a miss belongs to the day it happened.

    A drawing rule and nothing else, on the same line R17 took: the widget stays
    on the desk with its date and its status untouched, and drift and delta go
    on counting it. A widget with no `group_id` — every widget of a desk written
    before Q34, and every practice that promises once a day — is never touched
    by this.
    """
    if widget.group_id is None:
        return False
    return widget.group_id != group_key(widget.subject_id, now.date())


def _today_widgets(widgets: Sequence[Widget], now: datetime) -> list[Widget]:
    """Live Today tiles, plus done of this calendar day — even if still in Lifetime."""
    seen: set[str] = set()
    chosen: list[Widget] = []
    for widget in widgets:
        if widget.status in _HIDDEN_TODAY:
            continue
        if belongs_to_a_closed_day(widget, now):
            continue
        if widget.status == WidgetStatus.done:
            if not _is_done_today(widget, now):
                continue
        elif widget.section != WidgetSection.today:
            continue
        if widget.id in seen:
            continue
        seen.add(widget.id)
        chosen.append(widget)
    return chosen


def lid_projection(
    now: datetime,
    subjects: Sequence[Subject],
    instances: Sequence[Instance],
    widgets: Sequence[Widget],
) -> LidProjection:
    """Project the lid.

    Empty Today with no commitments and no drift → today empty, no card.
    Empty Today while a practice missed its cadence → one drift card in today.
    Done today stays in Today (band today_done), after the live tiles.
    Done on another calendar day is not drawn on Today.
    Rank v0 inside a non-empty Today. The morning card is one object: a drift
    ask when a period was missed, otherwise the calm delta line (Q6), and
    never both — the drift card carries the same subject louder.
    One practice draws one tile: a reminder whose hours today's group already
    says is not put in any section (R17). It stays on the desk and keeps
    ringing — this is a view, not the table.
    """
    card = drift_card(subjects, instances, now)
    # The morning reads the desk, not the drawing: hiding a tile must not be
    # able to wake a delta line that the tile itself was answering (Q6).
    delta = delta_card(subjects, instances, widgets, now) if card is None else None
    visible = _without_paused(subjects, widgets)
    visible = _without_repeated_reminders(now, subjects, instances, visible)

    today_widgets = _today_widgets(visible, now)
    today_ids = {widget.id for widget in today_widgets}
    lifetime = [
        widget
        for widget in visible
        if widget.section == WidgetSection.lifetime
        and widget.id not in today_ids
        and widget.status != WidgetStatus.done
    ]
    soon = [widget for widget in visible if widget.section == WidgetSection.soon]
    postponed = [
        widget for widget in visible if widget.section == WidgetSection.postponed
    ]

    today: list[WidgetTodayItem | DriftTodayItem | DeltaTodayItem] = [
        WidgetTodayItem(band=widget_rank_band(widget, now), widget=widget)
        for widget in today_widgets
    ]
    if card is not None:
        today.append(DriftTodayItem(drift_card=card))
    elif delta is not None:
        today.append(DeltaTodayItem(delta_card=delta))

    today.sort(key=lambda item: _sort_key(item, now))

    return LidProjection(
        today=today,
        lifetime=sorted(lifetime, key=lambda widget: widget.id),
        soon=sorted(soon, key=lambda widget: widget.id),
        postponed=sorted(postponed, key=lambda widget: widget.id),
        drift_card=card,
        delta_card=delta,
    )
