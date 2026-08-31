"""Talk tools. The model proposes calls; this module validates and applies them.

Pain is checked before a raise of target or cadence is applied — not hoped
for in a prompt. Unvalidated text never becomes payload. A cue without
`surface` is rejected here even though `add_cue` can default a surface
when called from tests.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, time
from typing import Any

from pydantic import TypeAdapter, ValidationError

from facio_domain.cues import add_cue
from facio_domain.drift import settle_talk_answer, times_per_week
from facio_domain.models import (
    Cadence,
    ChecklistItem,
    Cue,
    CueKind,
    CueMedia,
    CueOrigin,
    CueSurface,
    Desk,
    Instance,
    InstanceStatus,
    LinkMedia,
    PhotoMedia,
    Subject,
    SubjectStatus,
    Target,
    Widget,
    WidgetPayload,
    WidgetSection,
    WidgetStatus,
    WidgetType,
    Window,
)
from facio_domain.reminder import reminder_fire_at, window_from_closing
from facio_domain.runtime import (
    build_beats,
    build_checklist_items,
    build_seconds,
    checklist_progress,
    pause_timer,
    set_checklist_done,
    stepper_beats,
    stepper_position,
)
from facio_domain.subjects import freeze_subject, retire_subject, shrink_subject, thaw_subject

TOOL_NAMES = (
    "list_desk",
    "get_widget",
    "get_subject",
    "set_cadence",
    "shrink_subject",
    "retire_subject",
    "freeze_subject",
    "thaw_subject",
    "create_widget",
    "update_widget",
    "archive_widget",
    "complete",
    "skip",
    "postpone",
    "move_to_date",
    "set_reminder",
    "list_cues",
    "add_cue",
)

PAIN_FORBIDS_RAISE = "pain_forbids_raise"
SURFACE_REQUIRED = "surface_required"
# The same thought as `surface_required`: a cue with nowhere to appear is not a
# cue, and a practice with no rhythm is not a practice — it is a daily planner
# entry (06 never-do #14). `none` is a legal cadence for a one-off, but it must
# be said, not inherited from a default (05: an intent becomes a subject *with a
# cadence*). Guessing a rhythm for the person would be a silent desk rewrite.
CADENCE_REQUIRED = "cadence_required"
UNKNOWN_TOOL = "unknown_tool"
NOT_FOUND = "not_found"
INVALID = "invalid"
# Named-field refusals: the turn can fix these itself on the next round. The
# code names the field, it does not guess the right value — normalising a
# surface value sitting in `kind` would be a silent desk rewrite (never-do AI #2).
INVALID_KIND = "invalid_kind"
INVALID_SURFACE = "invalid_surface"
# `quote` is the phrase the person selected, stored **as text** (04 Cue). An
# offset into a message — a dict, a pair of numbers — dangles the moment the
# method changes, so it is refused instead of being coerced into something.
INVALID_QUOTE = "invalid_quote"
# At most one media item per cue, and it is `photo` (her own picture) or `link`
# (04 Cue). A list, or a third kind, is refused — not trimmed down to the first.
INVALID_MEDIA = "invalid_media"
# A type with no runtime behind it would land on the lid and vanish (В1.1).
# The gate lifts **per type**, together with that type's runtime and its
# projection — never as one flag — because a type without cadence, a do-time
# cue and drift is a planner line, not a practice (never-do #14).
UNSUPPORTED_WIDGET_TYPE = "unsupported_widget_type"
# Types whose runtime exists on both sides (law + lid). Everything else in
# `WidgetType` is still refused by `create_widget`; the enum in the tool
# schema is deliberately not narrowed — the model may ask, apply says no.
RUNNABLE_TYPES = frozenset(
    {
        WidgetType.counter,
        WidgetType.tick,
        WidgetType.reminder,
        WidgetType.checklist,
        WidgetType.timer,
        WidgetType.stepper,
    }
)
# A checklist with no lines is an empty tile: nothing to tick, nothing to
# finish. Named like the other field refusals so the turn can fix itself.
INVALID_ITEMS = "invalid_items"
# A timer with no length is a stopwatch, and a stopwatch has no do-time to
# aim at: «медитация» without «10 минут» is a practice, not a timer.
INVALID_SECONDS = "invalid_seconds"
# A stepper with no beats is a title on the lid. The type exists because a
# subject needs takts (Q1); without them it is a tick with extra chrome.
INVALID_BEATS = "invalid_beats"
# Hours of a window arrive as clock strings — «10:00», «16:30» — one or a list
# (Q34). Anything else is refused by name so the turn can fix itself.
INVALID_HOURS = "invalid_hours"
# `remove_hours` that would empty the window. A window with no hour cannot fire
# and cannot be drawn; going quiet is `postpone` or `archive_widget`.
HOURS_REQUIRED = "hours_required"

_MEDIA = TypeAdapter(CueMedia)


@dataclass
class ToolOutcome:
    desk: Desk
    name: str
    ok: bool
    data: dict[str, Any]
    error: str | None = None
    mutated: bool = False
    snapshot_widget_ids: list[str] = field(default_factory=list)


def apply_tool(
    desk: Desk,
    name: str,
    arguments: dict[str, Any] | None,
    *,
    pain: bool,
    now: datetime,
    origin: CueOrigin | None = None,
) -> ToolOutcome:
    """Apply one tool. Pain blocks a raise before the desk is copied."""
    args = dict(arguments or {})
    if name not in TOOL_NAMES:
        return ToolOutcome(desk=desk, name=name, ok=False, data={}, error=UNKNOWN_TOOL)
    if pain and _would_raise(desk, name, args):
        return ToolOutcome(desk=desk, name=name, ok=False, data={}, error=PAIN_FORBIDS_RAISE)
    next_desk = desk.model_copy(deep=True)
    try:
        outcome = _DISPATCH[name](next_desk, args, now=now, origin=origin)
    except ToolFail as error:
        return ToolOutcome(desk=desk, name=name, ok=False, data={}, error=error.code)
    if outcome.ok and outcome.mutated:
        _settle_drift_answers(desk, outcome.desk, now)
    return outcome


def _settle_drift_answers(before: Desk, after: Desk, now: datetime) -> None:
    """The one seam where talk meets the drift ladder (`drift.settle_talk_answer`).

    Every mutating tool passes through here, so the rule needs no list of tool
    names and no copy inside `_set_cadence` / `_shrink` / `_retire` / `_freeze`:
    the law is handed the subject before and after and decides for itself
    whether the commitment went down. A future tool that shrinks a practice is
    covered the day it is written, and one that does not, is not.
    """
    was = {subject.id: subject for subject in before.subjects}
    for subject in list(after.subjects):
        earlier = was.get(subject.id)
        if earlier is None:
            continue
        _replace_subject(after, settle_talk_answer(earlier, subject, now))


class ToolFail(Exception):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def snapshot_cards(desk: Desk, widget_ids: list[str]) -> list[dict[str, Any]]:
    """Centered chat cards: a picture, not a runtime."""
    cards: list[dict[str, Any]] = []
    seen: set[str] = set()
    by_id = {widget.id: widget for widget in desk.widgets}
    for widget_id in widget_ids:
        if widget_id in seen:
            continue
        widget = by_id.get(widget_id)
        if widget is None:
            continue
        seen.add(widget_id)
        cards.append(
            {
                "widget_id": widget.id,
                "subject_id": widget.subject_id,
                "instance_id": widget.instance_id,
                "version": widget.version,
                "title": widget.title,
                # `line` is the old wire: one finished Russian sentence. It
                # stays, verbatim, because a client built before this change
                # draws it and nothing else — but it is a fallback now, not the
                # source of truth.
                "line": _snapshot_line(desk, widget),
                # What the widget *was* at the moment the card was written:
                # numbers, not words. The person's language is the client's
                # business (it owns the catalog), and copy that lived on the
                # server could only ever be a second copy of it.
                "face": _snapshot_face(desk, widget),
                # The one part of the line that is genuinely data: the person's
                # own cue, in the words they said it in. Never product copy.
                "detail": _snapshot_detail(desk, widget),
            }
        )
    return cards


def _would_raise(desk: Desk, name: str, args: dict[str, Any]) -> bool:
    if name == "set_cadence":
        subject = _subject(desk, str(args.get("subject_id", "")))
        if subject is None:
            return False
        proposed = _cadence_from_args(args, fallback=subject.cadence)
        return times_per_week(proposed) > times_per_week(subject.cadence)
    if name == "update_widget":
        target = args.get("target")
        if target is None:
            return False
        widget = _widget(desk, str(args.get("widget_id", "")))
        if widget is None:
            return False
        current = _goal_for(desk, widget)
        return int(target) > current
    return False


def _cadence_from_args(args: dict[str, Any], *, fallback: Cadence) -> Cadence:
    period = args.get("period", fallback.period)
    if period == "none":
        return Cadence.none()
    count = args.get("count", fallback.count)
    if count is None:
        raise ToolFail(INVALID)
    if period not in ("day", "week"):
        raise ToolFail(INVALID)
    try:
        return Cadence.of(int(count), period)
    except (TypeError, ValueError) as error:
        raise ToolFail(INVALID) from error


def _cadence_for_new_subject(args: dict[str, Any]) -> Cadence:
    """A new subject needs a rhythm named out loud. No default is substituted.

    `{"period": "none"}` is accepted — a one-off is a legal practice ([04] «a
    finished thing»). What is refused is the *absence* of the argument.
    """
    raw = args.get("cadence")
    if not isinstance(raw, dict) or raw.get("period") is None:
        raise ToolFail(CADENCE_REQUIRED)
    return _cadence_from_args(raw, fallback=Cadence.none())


def _goal_for(desk: Desk, widget: Widget) -> int:
    subject = _subject(desk, widget.subject_id)
    if subject is not None and subject.target is not None:
        return subject.target.goal
    return widget.payload.target or 0


def _subject(desk: Desk, subject_id: str) -> Subject | None:
    return next((row for row in desk.subjects if row.id == subject_id), None)


def _widget(desk: Desk, widget_id: str) -> Widget | None:
    return next((row for row in desk.widgets if row.id == widget_id), None)


def _require_subject(desk: Desk, subject_id: str) -> Subject:
    subject = _subject(desk, subject_id)
    if subject is None:
        raise ToolFail(NOT_FOUND)
    return subject


def _require_widget(desk: Desk, widget_id: str) -> Widget:
    widget = _widget(desk, widget_id)
    if widget is None:
        raise ToolFail(NOT_FOUND)
    return widget


def _replace_subject(desk: Desk, subject: Subject) -> None:
    desk.subjects = [subject if row.id == subject.id else row for row in desk.subjects]


def _replace_widget(desk: Desk, widget: Widget) -> None:
    desk.widgets = [widget if row.id == widget.id else row for row in desk.widgets]


def _replace_instance(desk: Desk, instance: Instance) -> None:
    desk.instances = [instance if row.id == instance.id else row for row in desk.instances]


def _bump(widget: Widget) -> Widget:
    return widget.model_copy(update={"version": widget.version + 1})


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


def _parse_clock(raw: str) -> time:
    parts = raw.split(":")
    if len(parts) < 2:
        raise ToolFail(INVALID)
    hour = int(parts[0])
    minute = int(parts[1])
    second = int(parts[2]) if len(parts) > 2 else 0
    return time(hour, minute, second)


def _parse_when(raw: str) -> datetime:
    try:
        return datetime.fromisoformat(raw)
    except ValueError as error:
        raise ToolFail(INVALID) from error


def _do_time_cue(desk: Desk, subject_id: str) -> Cue | None:
    matches = [cue for cue in desk.cues if cue.subject_id == subject_id and cue.surface == CueSurface.do_time]
    return matches[-1] if matches else None


def _timing_cue(desk: Desk, subject_id: str) -> Cue | None:
    matches = [cue for cue in desk.cues if cue.subject_id == subject_id and cue.surface == CueSurface.timing]
    return matches[-1] if matches else None


def _snapshot_face(desk: Desk, widget: Widget) -> dict[str, Any]:
    """The state of one widget at write time, as numbers.

    A snapshot is a picture of the moment it was written ([04] «Snapshot and
    chapter»), so this reads the desk that is being sent back — the desk the
    turn just produced — and is never recomputed later against a newer one.
    The client repaints it from these fields with its own catalog; the same
    discipline `InstanceFaceLaw` keeps in the carousel, one wire further out.
    """
    subject = _subject(desk, widget.subject_id)
    if subject is not None and subject.status == SubjectStatus.paused:
        return {"kind": "paused"}
    if widget.type == WidgetType.counter:
        # No goal — no goal drawn. «0 / 0» is a target the person never named.
        return {"kind": "counter", "count": widget.payload.count or 0, "goal": widget.payload.target}
    if widget.type == WidgetType.tick:
        return {"kind": "tick", "done": bool(widget.payload.done or widget.status == WidgetStatus.done)}
    if widget.type == WidgetType.checklist:
        done, total = checklist_progress(widget.payload)
        return {"kind": "checklist", "done": done, "total": total}
    if widget.type == WidgetType.stepper:
        beats = stepper_beats(widget.payload)
        if not beats:
            return {"kind": "none"}
        return {"kind": "stepper", "step": stepper_position(widget.payload) + 1, "total": len(beats)}
    if widget.type == WidgetType.timer:
        return {"kind": "timer", "seconds": widget.payload.seconds or 0}
    if widget.type == WidgetType.reminder:
        fire = widget.payload.fire_at or widget.when
        closes_at = None
        if subject is not None and subject.window is not None and subject.window.closes_at is not None:
            closes_at = subject.window.closes_at.isoformat()
        return {
            "kind": "reminder",
            "clock": fire.strftime("%H:%M:%S") if fire else None,
            "closes_at": closes_at,
            "skipped": widget.status == WidgetStatus.skipped,
        }
    return {"kind": "none"}


def _snapshot_detail(desk: Desk, widget: Widget) -> str | None:
    """The cue that rode under the number, in the person's own words.

    Data, not copy: it is quoted from the conversation, so it travels. The door
    («the gym shuts at 22») is *not* here — that sentence is ours, and it is
    rebuilt on the client from `closes_at`.
    """
    if widget.type == WidgetType.reminder:
        cue = _timing_cue(desk, widget.subject_id)
    else:
        cue = _do_time_cue(desk, widget.subject_id)
    return cue.text if cue else None


def _snapshot_line(desk: Desk, widget: Widget) -> str:
    subject = _subject(desk, widget.subject_id)
    if subject is not None and subject.status == SubjectStatus.paused:
        return "на паузе"
    if widget.type == WidgetType.counter:
        count = widget.payload.count or 0
        target = widget.payload.target
        cue = _do_time_cue(desk, widget.subject_id)
        # No goal — no goal drawn. «0 / 0» is a target the person never named.
        base = f"{count} / {target}" if target else f"{count}"
        return f"{base} · {cue.text}" if cue else base
    if widget.type == WidgetType.tick:
        return "готово" if widget.payload.done or widget.status == WidgetStatus.done else "не сделано"
    if widget.type == WidgetType.checklist:
        # A picture of the list, not the list running in the bubble
        # (never-do #6): how many lines and the do-time line, nothing tickable.
        done, total = checklist_progress(widget.payload)
        cue = _do_time_cue(desk, widget.subject_id)
        base = f"{done} / {total}"
        return f"{base} · {cue.text}" if cue else base
    if widget.type == WidgetType.stepper:
        # A picture of where the sequence stands, not beats to press
        # (never-do #6): the tile is not a live stepper and neither is this.
        beats = stepper_beats(widget.payload)
        cue = _do_time_cue(desk, widget.subject_id)
        base = f"{stepper_position(widget.payload) + 1} / {len(beats)}" if beats else widget.title
        return f"{base} · {cue.text}" if cue else base
    if widget.type == WidgetType.timer:
        # A picture of the timer, not the timer running in the bubble
        # (never-do #6): the length, and the do-time line under it.
        total = widget.payload.seconds or 0
        cue = _do_time_cue(desk, widget.subject_id)
        base = _clock_phrase(total)
        return f"{base} · {cue.text}" if cue else base
    if widget.type == WidgetType.reminder:
        if widget.status == WidgetStatus.skipped:
            return "сегодня нет"
        fire = widget.payload.fire_at or widget.when
        clock = fire.strftime("%H:%M") if fire else ""
        door = None
        if subject is not None and subject.window is not None and subject.window.closes_at is not None:
            door = _door_phrase(subject.window.closes_at)
        cue = _timing_cue(desk, widget.subject_id)
        detail = door or (cue.text if cue else "")
        return f"{clock} · {detail}".strip(" ·") if detail else clock
    return widget.title


def _clock_phrase(seconds: int) -> str:
    """`mm:ss`, the way a timer face reads. Language-free on purpose."""
    minutes, rest = divmod(max(0, seconds), 60)
    return f"{minutes}:{rest:02d}"


def _door_phrase(closes_at: time) -> str:
    if closes_at.minute:
        return f"зал до {closes_at.hour}:{closes_at.minute:02d}"
    return f"зал до {closes_at.hour}"


def _dump_subject(subject: Subject) -> dict[str, Any]:
    return subject.model_dump(mode="json")


def _dump_widget(widget: Widget) -> dict[str, Any]:
    return widget.model_dump(mode="json", exclude_none=True)


def _list_desk(desk: Desk, args: dict[str, Any], **_: Any) -> ToolOutcome:
    del args
    return ToolOutcome(
        desk=desk,
        name="list_desk",
        ok=True,
        data={
            "subjects": [
                {
                    "id": subject.id,
                    "title": subject.title,
                    "status": subject.status,
                    "cadence": subject.cadence.model_dump(mode="json"),
                    "target": subject.target.model_dump() if subject.target else None,
                }
                for subject in desk.subjects
            ],
            "widgets": [
                {
                    "id": widget.id,
                    "type": widget.type,
                    "title": widget.title,
                    "section": widget.section,
                    "status": widget.status,
                    "subject_id": widget.subject_id,
                }
                for widget in desk.widgets
            ],
        },
    )


def _get_widget(desk: Desk, args: dict[str, Any], **_: Any) -> ToolOutcome:
    widget = _require_widget(desk, str(args.get("widget_id", "")))
    return ToolOutcome(desk=desk, name="get_widget", ok=True, data=_dump_widget(widget))


def _get_subject(desk: Desk, args: dict[str, Any], **_: Any) -> ToolOutcome:
    subject = _require_subject(desk, str(args.get("subject_id", "")))
    return ToolOutcome(desk=desk, name="get_subject", ok=True, data=_dump_subject(subject))


def _set_cadence(desk: Desk, args: dict[str, Any], **_: Any) -> ToolOutcome:
    subject = _require_subject(desk, str(args.get("subject_id", "")))
    cadence = _cadence_from_args(args, fallback=subject.cadence)
    _replace_subject(desk, subject.model_copy(update={"cadence": cadence}))
    return ToolOutcome(
        desk=desk,
        name="set_cadence",
        ok=True,
        data={"subject_id": subject.id, "cadence": cadence.model_dump(mode="json")},
        mutated=True,
        snapshot_widget_ids=_widgets_for(desk, subject.id),
    )


def _shrink(desk: Desk, args: dict[str, Any], **_: Any) -> ToolOutcome:
    subject = _require_subject(desk, str(args.get("subject_id", "")))
    weekly = Cadence.of(1, "week")
    next_subject = shrink_subject(subject).model_copy(update={"cadence": weekly})
    _replace_subject(desk, next_subject)
    return ToolOutcome(
        desk=desk,
        name="shrink_subject",
        ok=True,
        data={"subject_id": subject.id, "cadence": weekly.model_dump(mode="json")},
        mutated=True,
        snapshot_widget_ids=_widgets_for(desk, subject.id),
    )


def _retire(desk: Desk, args: dict[str, Any], **_: Any) -> ToolOutcome:
    subject = _require_subject(desk, str(args.get("subject_id", "")))
    _replace_subject(desk, retire_subject(subject))
    return ToolOutcome(
        desk=desk,
        name="retire_subject",
        ok=True,
        data={"subject_id": subject.id, "status": SubjectStatus.retired},
        mutated=True,
        snapshot_widget_ids=_widgets_for(desk, subject.id),
    )


def _freeze(desk: Desk, args: dict[str, Any], *, now: datetime, **_: Any) -> ToolOutcome:
    subject = _require_subject(desk, str(args.get("subject_id", "")))
    if subject.status == SubjectStatus.retired:
        raise ToolFail(INVALID)
    next_subject = freeze_subject(subject, now)
    _replace_subject(desk, next_subject)
    paused_at = next_subject.paused_at
    return ToolOutcome(
        desk=desk,
        name="freeze_subject",
        ok=True,
        data={
            "subject_id": subject.id,
            "status": SubjectStatus.paused,
            "paused_at": paused_at.isoformat(timespec="seconds") if paused_at else None,
        },
        mutated=True,
        snapshot_widget_ids=_widgets_for(desk, subject.id),
    )


def _thaw(desk: Desk, args: dict[str, Any], **_: Any) -> ToolOutcome:
    subject = _require_subject(desk, str(args.get("subject_id", "")))
    if subject.status != SubjectStatus.paused:
        raise ToolFail(INVALID)
    _replace_subject(desk, thaw_subject(subject))
    for widget in desk.widgets:
        if widget.subject_id == subject.id and widget.status == WidgetStatus.skipped:
            _replace_widget(desk, widget.model_copy(update={"status": WidgetStatus.ready}))
    return ToolOutcome(
        desk=desk,
        name="thaw_subject",
        ok=True,
        data={"subject_id": subject.id, "status": SubjectStatus.active},
        mutated=True,
        snapshot_widget_ids=_widgets_for(desk, subject.id),
    )


def _create_widget(desk: Desk, args: dict[str, Any], *, now: datetime, **_: Any) -> ToolOutcome:
    raw_type = str(args.get("type", ""))
    title = str(args.get("title", "")).strip()
    subject_id = str(args.get("subject_id", "")).strip()
    if not raw_type or not title or not subject_id:
        raise ToolFail(INVALID)
    try:
        widget_type = WidgetType(raw_type)
        section = WidgetSection(str(args.get("section") or "today"))
    except ValueError as error:
        raise ToolFail(INVALID) from error
    if widget_type not in RUNNABLE_TYPES:
        raise ToolFail(UNSUPPORTED_WIDGET_TYPE)
    items = _checklist_items_for(widget_type, args)
    seconds = _seconds_for(widget_type, args)
    beats = _beats_for(widget_type, args)
    subject = _subject(desk, subject_id)
    if subject is None:
        cadence = _cadence_for_new_subject(args)
        subject = Subject(id=subject_id, title=title, cadence=cadence)
        desk.subjects.append(subject)
    instance_id = _new_id(f"{subject_id}-open")
    widget_id = str(args.get("id") or _new_id(widget_type.value))
    instance = Instance(id=instance_id, subject_id=subject_id, when=now, status=InstanceStatus.prepared)
    desk.instances.append(instance)
    if instance_id not in subject.instance_ids:
        subject.instance_ids.append(instance_id)
        _replace_subject(desk, subject)
    payload = WidgetPayload()
    target = args.get("target")
    if target is not None:
        payload.target = int(target)
        payload.count = int(args.get("count", target))
        current = subject.target.current if subject.target else int(args.get("count", 0))
        _replace_subject(desk, subject.model_copy(update={"target": Target(current=current, goal=int(target))}))
    if widget_type == WidgetType.tick:
        payload.done = False
    if items is not None:
        payload.items = items
    if seconds is not None:
        # A fresh timer is standing still: the length, nothing banked, no run.
        payload.seconds = seconds
        payload.elapsed = 0
    if beats is not None:
        payload.beats = beats
        payload.current = 0
    widget = Widget(
        id=widget_id,
        type=widget_type,
        title=title,
        payload=payload,
        status=WidgetStatus.ready,
        section=section,
        subject_id=subject_id,
        instance_id=instance_id,
        tile_size=_default_tile(widget_type),
    )
    desk.widgets.append(widget)
    return ToolOutcome(
        desk=desk,
        name="create_widget",
        ok=True,
        data=_dump_widget(widget),
        mutated=True,
        snapshot_widget_ids=[widget.id],
    )


def _checklist_items_for(
    widget_type: WidgetType, args: dict[str, Any]
) -> list[ChecklistItem] | None:
    """The lines of a new checklist. A checklist without them does not land.

    Other types simply have no items: passing them is not an error, it is
    ignored, the way an unread key in `extra` is.
    """
    if widget_type != WidgetType.checklist:
        return None
    items = build_checklist_items(args.get("items"))
    if not items:
        raise ToolFail(INVALID_ITEMS)
    return items


def _seconds_for(widget_type: WidgetType, args: dict[str, Any]) -> int | None:
    """The length of a new timer. A timer without one does not land."""
    if widget_type != WidgetType.timer:
        return None
    seconds = build_seconds(args.get("seconds"))
    if seconds is None:
        raise ToolFail(INVALID_SECONDS)
    return seconds


def _beats_for(widget_type: WidgetType, args: dict[str, Any]) -> list[str] | None:
    """The beats of a new stepper. Without them the type has no reason to be."""
    if widget_type != WidgetType.stepper:
        return None
    beats = build_beats(args.get("beats"))
    if not beats:
        raise ToolFail(INVALID_BEATS)
    return beats


def _default_tile(widget_type: WidgetType) -> str:
    """Type owns the shape (never-do #8). Sizes from Q18's preferred set.

    A type with no size of its own would fall back to the packer's default
    cell and sit in the grid as a hole, so every runnable type names one.
    """
    if widget_type in {WidgetType.reminder, WidgetType.checklist, WidgetType.stepper}:
        return "4x2"
    if widget_type in {WidgetType.counter, WidgetType.tick, WidgetType.timer}:
        return "2x2"
    return "4x1"


def _update_widget(desk: Desk, args: dict[str, Any], **_: Any) -> ToolOutcome:
    widget = _require_widget(desk, str(args.get("widget_id", "")))
    payload = widget.payload.model_copy()
    title = widget.title
    if "title" in args and args["title"] is not None:
        title = str(args["title"])
    if "target" in args and args["target"] is not None:
        payload.target = int(args["target"])
        subject = _require_subject(desk, widget.subject_id)
        current = subject.target.current if subject.target else payload.count or 0
        _replace_subject(desk, subject.model_copy(update={"target": Target(current=current, goal=int(args["target"]))}))
    if "items" in args and args["items"] is not None:
        # Restructuring the list is a structural edit, same as retitling it.
        # The lines arrive whole: merging half a list into ticked rows behind
        # the person's back is the silent rewrite AI #2 forbids.
        rebuilt = build_checklist_items(args["items"])
        if widget.type != WidgetType.checklist or not rebuilt:
            raise ToolFail(INVALID_ITEMS)
        payload.items = rebuilt
    if "seconds" in args and args["seconds"] is not None:
        rebuilt = build_seconds(args["seconds"])
        if widget.type != WidgetType.timer or rebuilt is None:
            raise ToolFail(INVALID_SECONDS)
        payload.seconds = rebuilt
    if "beats" in args and args["beats"] is not None:
        rebuilt = build_beats(args["beats"])
        if widget.type != WidgetType.stepper or not rebuilt:
            raise ToolFail(INVALID_BEATS)
        payload.beats = rebuilt
        # A rewritten sequence keeps the person where they stand, clamped into
        # the beats that now exist — never silently sent back to the start.
        payload.current = min(stepper_position(payload), len(rebuilt) - 1)
    if "count" in args and args["count"] is not None:
        payload.count = int(args["count"])
        if widget.type == WidgetType.counter:
            subject = _require_subject(desk, widget.subject_id)
            if subject.target is not None:
                _replace_subject(
                    desk,
                    subject.model_copy(
                        update={"target": Target(current=int(args["count"]), goal=subject.target.goal)}
                    ),
                )
    next_widget = _bump(widget.model_copy(update={"title": title, "payload": payload}))
    _replace_widget(desk, next_widget)
    return ToolOutcome(
        desk=desk,
        name="update_widget",
        ok=True,
        data=_dump_widget(next_widget),
        mutated=True,
        snapshot_widget_ids=[next_widget.id],
    )


def _archive_widget(desk: Desk, args: dict[str, Any], **_: Any) -> ToolOutcome:
    widget = _require_widget(desk, str(args.get("widget_id", "")))
    next_widget = _bump(widget.model_copy(update={"status": WidgetStatus.archived}))
    _replace_widget(desk, next_widget)
    return ToolOutcome(
        desk=desk,
        name="archive_widget",
        ok=True,
        data={"widget_id": widget.id, "status": WidgetStatus.archived},
        mutated=True,
        snapshot_widget_ids=[widget.id],
    )


def _complete(desk: Desk, args: dict[str, Any], *, now: datetime, **_: Any) -> ToolOutcome:
    widget = _require_widget(desk, str(args.get("widget_id", "")))
    payload = widget.payload.model_copy()
    if widget.type == WidgetType.tick:
        payload.done = True
    if widget.type == WidgetType.checklist:
        # Finishing the list finishes its lines. The tile stops showing
        # «2 из 5» next to a done instance — one truth, not two.
        payload = set_checklist_done(payload, True)
    if widget.type == WidgetType.timer:
        # A finished sitting is not a running one: bank the seconds it took and
        # stop the run, or the tile would keep counting past a closed case.
        payload = pause_timer(payload, now)
    if widget.type == WidgetType.stepper:
        # Finished means standing on the last beat. Not reset to the first:
        # next time is a new instance, and that one starts at zero.
        beats = stepper_beats(payload)
        if beats:
            payload = payload.model_copy(update={"current": len(beats) - 1})
    next_widget = widget.model_copy(update={"status": WidgetStatus.done, "when": now, "payload": payload})
    _replace_widget(desk, next_widget)
    _complete_instance(desk, widget.instance_id, now)
    return ToolOutcome(
        desk=desk,
        name="complete",
        ok=True,
        data={"widget_id": widget.id, "status": WidgetStatus.done},
        mutated=True,
        snapshot_widget_ids=[widget.id],
    )


def _skip(desk: Desk, args: dict[str, Any], **_: Any) -> ToolOutcome:
    widget = _require_widget(desk, str(args.get("widget_id", "")))
    next_widget = widget.model_copy(update={"status": WidgetStatus.skipped})
    _replace_widget(desk, next_widget)
    return ToolOutcome(
        desk=desk,
        name="skip",
        ok=True,
        data={"widget_id": widget.id, "status": WidgetStatus.skipped},
        mutated=True,
        snapshot_widget_ids=[widget.id],
    )


def _postpone(desk: Desk, args: dict[str, Any], **_: Any) -> ToolOutcome:
    widget = _require_widget(desk, str(args.get("widget_id", "")))
    when = widget.when
    if args.get("when"):
        when = _parse_when(str(args["when"]))
    next_widget = widget.model_copy(
        update={"section": WidgetSection.postponed, "status": WidgetStatus.snoozed, "when": when}
    )
    _replace_widget(desk, next_widget)
    return ToolOutcome(
        desk=desk,
        name="postpone",
        ok=True,
        data={"widget_id": widget.id, "section": WidgetSection.postponed},
        mutated=True,
        snapshot_widget_ids=[widget.id],
    )


def _move_to_date(desk: Desk, args: dict[str, Any], **_: Any) -> ToolOutcome:
    widget = _require_widget(desk, str(args.get("widget_id", "")))
    when = _parse_when(str(args.get("when", "")))
    next_widget = widget.model_copy(update={"when": when, "section": WidgetSection.today})
    _replace_widget(desk, next_widget)
    instance = next((row for row in desk.instances if row.id == widget.instance_id), None)
    if instance is not None:
        _replace_instance(desk, instance.model_copy(update={"when": when}))
    return ToolOutcome(
        desk=desk,
        name="move_to_date",
        ok=True,
        data={"widget_id": widget.id, "when": when.isoformat(timespec="seconds")},
        mutated=True,
        snapshot_widget_ids=[widget.id],
    )


def _clock_list(raw: Any) -> list[time]:
    """Hours off the wire. One string is a list of one — the old shape."""
    if raw is None:
        return []
    if isinstance(raw, (str, time)):
        raw = [raw]
    if not isinstance(raw, (list, tuple)):
        raise ToolFail(INVALID_HOURS)
    hours: list[time] = []
    for item in raw:
        if isinstance(item, time):
            hours.append(item)
        elif isinstance(item, str):
            hours.append(_parse_clock(item))
        else:
            raise ToolFail(INVALID_HOURS)
    return hours


def _next_window(subject: Subject, args: dict[str, Any]) -> Window:
    """The window after this call. Hours are added, never quietly replaced.

    An hour the person named stays until they say to drop it (`remove_hours`):
    «в 10, 12 и 15» said over three turns is three hours, not the last one. The
    same hour twice is the same hour. The door keeps its own arithmetic — it
    still gives 19:00 out of 22:00, and it still never moves an hour that was
    spoken out loud.
    """
    added = _clock_list(args.get("hours")) + _clock_list(args.get("latest_by"))
    removed = set(_clock_list(args.get("remove_hours")))
    closes_raw = args.get("closes_at")
    if not added and not removed and not closes_raw:
        raise ToolFail(INVALID)
    stated = list(subject.window.hours) if subject.window is not None else []
    closes = subject.window.closes_at if subject.window is not None else None
    if closes_raw:
        closes = _parse_clock(str(closes_raw))
    hours = sorted({*stated, *added} - removed)
    if hours:
        return Window(hours=hours, closes_at=closes)
    if removed and stated:
        # Dropping the last hour is not "no reminder": a window with nothing in
        # it cannot fire and cannot be drawn. Quieting a practice is `postpone`
        # or `archive_widget`, and both of them are said, not inferred.
        raise ToolFail(HOURS_REQUIRED)
    if closes is None:
        raise ToolFail(INVALID)
    return window_from_closing(closes)


def _set_reminder(desk: Desk, args: dict[str, Any], *, now: datetime, **_: Any) -> ToolOutcome:
    subject = _require_subject(desk, str(args.get("subject_id", "")))
    window = _next_window(subject, args)
    _replace_subject(desk, subject.model_copy(update={"window": window}))
    fire_at = reminder_fire_at(subject, window, now.date())
    touched: list[str] = []
    for widget in list(desk.widgets):
        if widget.subject_id != subject.id or widget.type != WidgetType.reminder:
            continue
        payload = widget.payload.model_copy(update={"fire_at": fire_at})
        next_widget = _bump(widget.model_copy(update={"payload": payload, "when": fire_at}))
        _replace_widget(desk, next_widget)
        touched.append(widget.id)
        instance = next((row for row in desk.instances if row.id == widget.instance_id), None)
        if instance is not None and instance.status != InstanceStatus.completed:
            _replace_instance(desk, instance.model_copy(update={"when": fire_at}))
    if not touched:
        touched.append(_create_reminder_widget(desk, subject.id, fire_at))
    return ToolOutcome(
        desk=desk,
        name="set_reminder",
        ok=True,
        data={
            "subject_id": subject.id,
            # `latest_by` stays on the wire, first of the hours, so a turn and a
            # client written before Q34 read what they always read.
            "latest_by": window.hours[0].isoformat(timespec="seconds"),
            "hours": [hour.isoformat(timespec="seconds") for hour in window.hours],
            "closes_at": window.closes_at.isoformat(timespec="seconds") if window.closes_at else None,
        },
        mutated=True,
        snapshot_widget_ids=touched,
    )


def _create_reminder_widget(desk: Desk, subject_id: str, fire_at: datetime) -> str:
    subject = _require_subject(desk, subject_id)
    instance_id = _new_id(f"{subject_id}-open")
    widget_id = _new_id("reminder")
    desk.instances.append(
        Instance(id=instance_id, subject_id=subject_id, when=fire_at, status=InstanceStatus.prepared)
    )
    if instance_id not in subject.instance_ids:
        _replace_subject(
            desk,
            subject.model_copy(update={"instance_ids": [*subject.instance_ids, instance_id]}),
        )
    widget = Widget(
        id=widget_id,
        type=WidgetType.reminder,
        title=subject.title,
        payload=WidgetPayload(fire_at=fire_at),
        status=WidgetStatus.ready,
        when=fire_at,
        section=WidgetSection.today,
        subject_id=subject_id,
        instance_id=instance_id,
        tile_size=_default_tile(WidgetType.reminder),
    )
    desk.widgets.append(widget)
    return widget_id


def _list_cues(desk: Desk, args: dict[str, Any], **_: Any) -> ToolOutcome:
    subject_id = args.get("subject_id")
    cues = desk.cues if not subject_id else [cue for cue in desk.cues if cue.subject_id == subject_id]
    return ToolOutcome(
        desk=desk,
        name="list_cues",
        ok=True,
        data={"cues": [cue.model_dump(mode="json") for cue in cues]},
    )


def _optional_text(raw: Any) -> str | None:
    if raw is None:
        return None
    if not isinstance(raw, str):
        raise ToolFail(INVALID)
    return raw.strip() or None


def _quote_from_args(args: dict[str, Any]) -> str | None:
    raw = args.get("quote")
    if raw is None:
        return None
    if not isinstance(raw, str):
        raise ToolFail(INVALID_QUOTE)
    return raw.strip() or None


def _media_from_args(args: dict[str, Any]) -> CueMedia | None:
    raw = args.get("media")
    if raw is None:
        return None
    if isinstance(raw, (PhotoMedia, LinkMedia)):
        return raw
    if not isinstance(raw, dict):
        raise ToolFail(INVALID_MEDIA)
    try:
        return _MEDIA.validate_python(raw)
    except ValidationError as error:
        raise ToolFail(INVALID_MEDIA) from error


def _add_cue_tool(
    desk: Desk,
    args: dict[str, Any],
    *,
    origin: CueOrigin | None,
    **_: Any,
) -> ToolOutcome:
    if not args.get("surface"):
        raise ToolFail(SURFACE_REQUIRED)
    subject_id = str(args.get("subject_id", "")).strip()
    text = str(args.get("text", "")).strip()
    kind_raw = args.get("kind")
    if not subject_id or not text or not kind_raw:
        raise ToolFail(INVALID)
    _require_subject(desk, subject_id)
    try:
        kind = CueKind(str(kind_raw))
    except ValueError as error:
        raise ToolFail(INVALID_KIND) from error
    try:
        surface = CueSurface(str(args["surface"]))
    except ValueError as error:
        raise ToolFail(INVALID_SURFACE) from error
    cue_id = str(args.get("id") or _new_id("cue"))
    cue_origin = origin
    if args.get("chat_id") or args.get("message_id"):
        cue_origin = CueOrigin(
            chat_id=args.get("chat_id", origin.chat_id if origin else None),
            message_id=args.get("message_id", origin.message_id if origin else None),
        )
    cue = add_cue(
        id=cue_id,
        subject_id=subject_id,
        # The step the phrase belongs to. Dropping it put the answer on the
        # practice as a whole; the `?` lives on a step (05 «Ask about a phrase»).
        step_id=_optional_text(args.get("step_id")),
        kind=kind,
        text=text,
        surface=surface,
        quote=_quote_from_args(args),
        media=_media_from_args(args),
        origin=cue_origin,
    )
    existing = next((index for index, row in enumerate(desk.cues) if row.id == cue.id), None)
    if existing is None:
        desk.cues.append(cue)
    else:
        desk.cues[existing] = cue
    subject = _require_subject(desk, subject_id)
    if cue.id not in subject.cue_ids:
        _replace_subject(desk, subject.model_copy(update={"cue_ids": [*subject.cue_ids, cue.id]}))
    return ToolOutcome(
        desk=desk,
        name="add_cue",
        ok=True,
        data=cue.model_dump(mode="json"),
        mutated=True,
        snapshot_widget_ids=_widgets_for(desk, subject_id),
    )


def _complete_instance(desk: Desk, instance_id: str, now: datetime) -> None:
    instance = next((row for row in desk.instances if row.id == instance_id), None)
    if instance is None:
        return
    _replace_instance(desk, instance.model_copy(update={"status": InstanceStatus.completed, "when": now}))


def _widgets_for(desk: Desk, subject_id: str) -> list[str]:
    return [widget.id for widget in desk.widgets if widget.subject_id == subject_id]


_DISPATCH = {
    "list_desk": _list_desk,
    "get_widget": _get_widget,
    "get_subject": _get_subject,
    "set_cadence": _set_cadence,
    "shrink_subject": _shrink,
    "retire_subject": _retire,
    "freeze_subject": _freeze,
    "thaw_subject": _thaw,
    "create_widget": _create_widget,
    "update_widget": _update_widget,
    "archive_widget": _archive_widget,
    "complete": _complete,
    "skip": _skip,
    "postpone": _postpone,
    "move_to_date": _move_to_date,
    "set_reminder": _set_reminder,
    "list_cues": _list_cues,
    "add_cue": _add_cue_tool,
}
