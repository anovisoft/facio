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

from facio_domain.cues import add_cue
from facio_domain.models import (
    Cadence,
    Cue,
    CueKind,
    CueOrigin,
    CueSurface,
    Desk,
    Instance,
    InstanceStatus,
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
UNKNOWN_TOOL = "unknown_tool"
NOT_FOUND = "not_found"
INVALID = "invalid"
# Named-field refusals: the turn can fix these itself on the next round. The
# code names the field, it does not guess the right value — normalising a
# surface value sitting in `kind` would be a silent desk rewrite (never-do AI #2).
INVALID_KIND = "invalid_kind"
INVALID_SURFACE = "invalid_surface"
UNSUPPORTED_WIDGET_TYPE = "unsupported_widget_type"


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
        return _DISPATCH[name](next_desk, args, now=now, origin=origin)
    except ToolFail as error:
        return ToolOutcome(desk=desk, name=name, ok=False, data={}, error=error.code)


class ToolFail(Exception):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def times_per_week(cadence: Cadence) -> float:
    if cadence.period == "none" or cadence.count is None:
        return 0.0
    if cadence.period == "day":
        return float(cadence.count) * 7.0
    return float(cadence.count)


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
                "line": _snapshot_line(desk, widget),
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


def _snapshot_line(desk: Desk, widget: Widget) -> str:
    subject = _subject(desk, widget.subject_id)
    if subject is not None and subject.status == SubjectStatus.paused:
        return "на паузе"
    if widget.type == WidgetType.counter:
        count = widget.payload.count or 0
        target = widget.payload.target or 0
        cue = _do_time_cue(desk, widget.subject_id)
        base = f"{count} / {target}"
        return f"{base} · {cue.text}" if cue else base
    if widget.type == WidgetType.tick:
        return "готово" if widget.payload.done or widget.status == WidgetStatus.done else "не сделано"
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
    if widget_type in {WidgetType.checklist, WidgetType.timer, WidgetType.stepper}:
        raise ToolFail(UNSUPPORTED_WIDGET_TYPE)
    subject = _subject(desk, subject_id)
    if subject is None:
        cadence = _cadence_from_args(args, fallback=Cadence.none())
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


def _default_tile(widget_type: WidgetType) -> str:
    if widget_type == WidgetType.reminder:
        return "4x2"
    if widget_type in {WidgetType.counter, WidgetType.tick}:
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


def _set_reminder(desk: Desk, args: dict[str, Any], *, now: datetime, **_: Any) -> ToolOutcome:
    subject = _require_subject(desk, str(args.get("subject_id", "")))
    closes_raw = args.get("closes_at")
    latest_raw = args.get("latest_by")
    if latest_raw:
        latest = _parse_clock(str(latest_raw))
        if closes_raw:
            window = Window(latest_by=latest, closes_at=_parse_clock(str(closes_raw)))
        elif subject.window is not None:
            window = subject.window.model_copy(update={"latest_by": latest})
        else:
            window = Window(latest_by=latest)
    elif closes_raw:
        closes = _parse_clock(str(closes_raw))
        if subject.window is not None:
            window = subject.window.model_copy(update={"closes_at": closes})
        else:
            window = window_from_closing(closes)
    else:
        raise ToolFail(INVALID)
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
            "latest_by": window.latest_by.isoformat(timespec="seconds"),
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
        kind=kind,
        text=text,
        surface=surface,
        quote=args.get("quote"),
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
