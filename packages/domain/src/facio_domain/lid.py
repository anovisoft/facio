"""Lid projection. The lid is a view, not a table."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Never

from facio_domain.drift import drift_card
from facio_domain.models import (
    DriftAskState,
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
)

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


def _sort_key(item: WidgetTodayItem | DriftTodayItem, now: datetime) -> tuple:
    if isinstance(item, DriftTodayItem):
        return (_band_index(RankBand.drift_card), datetime.min, item.drift_card.subject_id)
    when = item.widget.when or now
    return (_band_index(item.band), when, item.widget.id)


def _today_widgets(widgets: Sequence[Widget], now: datetime) -> list[Widget]:
    """Live Today tiles, plus done of this calendar day — even if still in Lifetime."""
    seen: set[str] = set()
    chosen: list[Widget] = []
    for widget in widgets:
        if widget.status in _HIDDEN_TODAY:
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
    histories: Mapping[str, DriftAskState] | None = None,
) -> LidProjection:
    """Project the lid.

    Empty Today with no commitments and no drift → today empty, no card.
    Empty Today while a practice missed its cadence → one drift card in today.
    Done today stays in Today (band today_done), after the live tiles.
    Done on another calendar day is not drawn on Today.
    Rank v0 inside a non-empty Today. Unanswered morning is reserved; this
    step does not invent a morning engine.
    """
    card = drift_card(subjects, instances, now, histories)
    visible = _without_paused(subjects, widgets)

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

    today: list[WidgetTodayItem | DriftTodayItem] = [
        WidgetTodayItem(band=widget_rank_band(widget, now), widget=widget)
        for widget in today_widgets
    ]
    if card is not None:
        today.append(DriftTodayItem(drift_card=card))

    today.sort(key=lambda item: _sort_key(item, now))

    return LidProjection(
        today=today,
        lifetime=sorted(lifetime, key=lambda widget: widget.id),
        soon=sorted(soon, key=lambda widget: widget.id),
        postponed=sorted(postponed, key=lambda widget: widget.id),
        drift_card=card,
    )
