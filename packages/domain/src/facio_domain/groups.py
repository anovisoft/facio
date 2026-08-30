"""One tile for the occurrences of one subject inside one period (Q34).

The count stays in the law — seven checks are seven cases and seven widgets,
each closed on its own. What changes is the drawing: the lid draws the group
**once**, through `group_id`, the field 04 declared from the start and nothing
had ever used.

The face borrows the stepper's compactness — the next hour large, `3/7`, a row
of marks — and refuses its **pointer**. There is no "current beat" here: marks
are independent and unordered, because a pointer cannot record «did 10 and 15,
missed 12», and the miss is the product. Closing 15:00 closes 15:00; the 12:00
that was missed stays visibly missed.

Packing tiles is the client's job (there is no packer here), but the arithmetic
a tile paints is law: which widgets are one group, how many of them are closed,
and which hour is the next one still ahead. That much must not drift between
the phone and the service, so it lives here and is mirrored in `GroupLaw.swift`.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict, Field

from facio_domain.models import (
    Instance,
    Widget,
    WidgetStatus,
    WidgetType,
)

GROUP_SEPARATOR = ":"


def group_key(subject_id: str, day: date) -> str:
    """The id every occurrence of one subject on one day carries.

    Derived, not invented: the same subject on the same day always produces the
    same key, so topping the day up a second time re-stamps rather than splits.
    """
    return f"{subject_id}{GROUP_SEPARATOR}{day.isoformat()}"


class GroupMark(BaseModel):
    """One occurrence, as a mark on the group tile."""

    model_config = ConfigDict(extra="forbid")

    widget_id: str
    instance_id: str
    hour: time | None = None
    done: bool = False


class GroupFace(BaseModel):
    """What one group tile draws. A picture of the group, not a runtime."""

    model_config = ConfigDict(extra="forbid")

    group_id: str
    subject_id: str
    title: str
    next_hour: time | None = None
    done: int = 0
    total: int = 0
    marks: list[GroupMark] = Field(default_factory=list)


def is_closed(widget: Widget) -> bool:
    """Whether this occurrence is struck off. `skipped` is not `done`.

    A skipped check is a check that did not happen; drawing it closed would be
    the same lie as a pointer that forgets what it stepped over.
    """
    if widget.status == WidgetStatus.done:
        return True
    if widget.type == WidgetType.tick and widget.payload.done is True:
        return True
    return False


def grouped_ids(widgets: Sequence[Widget]) -> list[str]:
    """Every `group_id` on these widgets, in the order the first member appears.

    A group of one is still a group — but nothing calls it one: the lid only
    stamps `group_id` when a practice promised more than one occurrence in the
    period, so a widget without the field draws exactly as it always did.
    """
    seen: list[str] = []
    for widget in widgets:
        key = widget.group_id
        if key is not None and key not in seen:
            seen.append(key)
    return seen


def members(group_id: str, widgets: Sequence[Widget]) -> list[Widget]:
    return [widget for widget in widgets if widget.group_id == group_id]


def group_face(
    group_id: str,
    widgets: Sequence[Widget],
    instances: Sequence[Instance],
    now: datetime,
) -> GroupFace | None:
    """The face of one group, or nothing when no widget carries that id."""
    rows = members(group_id, widgets)
    if not rows:
        return None
    when_of = {instance.id: instance.when for instance in instances}
    marks = [
        GroupMark(
            widget_id=widget.id,
            instance_id=widget.instance_id,
            hour=_hour_of(widget, when_of),
            done=is_closed(widget),
        )
        for widget in rows
    ]
    marks.sort(key=lambda mark: (mark.hour or time.max, mark.widget_id))
    return GroupFace(
        group_id=group_id,
        subject_id=rows[0].subject_id,
        title=rows[0].title,
        next_hour=next_hour(marks, now),
        done=sum(1 for mark in marks if mark.done),
        total=len(marks),
        marks=marks,
    )


def next_hour(marks: Sequence[GroupMark], now: datetime) -> time | None:
    """The hour the tile shows large: the nearest one still ahead and still open.

    Past-and-missed is not promoted into the big number — the day already moved
    on — but it is not swept away either: the mark for it stays open in the row.
    When every hour of the day is behind, the first one still open is what is
    left to say; when nothing is open, the group is finished and there is no
    hour to show.
    """
    clock = now.time()
    open_marks = [mark for mark in marks if not mark.done and mark.hour is not None]
    ahead = [mark for mark in open_marks if mark.hour is not None and mark.hour >= clock]
    if ahead:
        return ahead[0].hour
    if open_marks:
        return open_marks[0].hour
    return None


def _hour_of(widget: Widget, when_of: dict[str, datetime]) -> time | None:
    when = when_of.get(widget.instance_id) or widget.when
    return when.time() if when is not None else None
