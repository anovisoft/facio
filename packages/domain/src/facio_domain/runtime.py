"""Runtimes of the catalog types (Q1), as pure functions over a payload.

One rule holds the whole file together: **no runtime state is stored twice**.
A checklist keeps its ticks and derives progress from them; a timer keeps the
moment its run began and derives the elapsed seconds; a stepper keeps one
position and derives whether it is on the last beat. Nothing here
writes a "progress" number into the desk — that would be a second truth about
the same thing, and the two would drift the first time a tick happened offline
(Q20: runtime progress merges per item, so it has to *be* per item).

Nothing here reaches for the clock on its own: `now` is passed in where a
runtime needs it, the way drift and the reminder hour do. No I/O, no model, no
side effects.
"""

from __future__ import annotations

from datetime import datetime

from facio_domain.models import ChecklistItem, WidgetPayload

# --- checklist ------------------------------------------------------------


def checklist_items(payload: WidgetPayload) -> list[ChecklistItem]:
    """The lines of the list. A checklist with no items is an empty list."""
    return list(payload.items or [])


def checklist_progress(payload: WidgetPayload) -> tuple[int, int]:
    """`(done, total)` — counted, never stored (04: drift is derived, so is this)."""
    items = checklist_items(payload)
    return sum(1 for item in items if item.done), len(items)


def checklist_is_done(payload: WidgetPayload) -> bool:
    """Every line ticked. An empty list is not done — there was nothing to do."""
    done, total = checklist_progress(payload)
    return total > 0 and done == total


def toggle_checklist_item(payload: WidgetPayload, item_id: str) -> WidgetPayload:
    """Flip one line. An unknown id changes nothing — a finger cannot invent a row."""
    items = checklist_items(payload)
    if not any(item.id == item_id for item in items):
        return payload
    flipped = [
        item.model_copy(update={"done": not item.done}) if item.id == item_id else item
        for item in items
    ]
    return payload.model_copy(update={"items": flipped})


def set_checklist_done(payload: WidgetPayload, done: bool) -> WidgetPayload:
    """Tick or untick every line at once — what «Готово» on Use means."""
    items = checklist_items(payload)
    if not items:
        return payload
    return payload.model_copy(
        update={"items": [item.model_copy(update={"done": done}) for item in items]}
    )


def build_checklist_items(raw: object) -> list[ChecklistItem] | None:
    """Read items off a tool call. Text-only lines are the common case.

    Accepts `["хлеб", "молоко"]` and `[{"text": "хлеб", "done": true}]`. Ids are
    filled in positionally when the caller did not name them, because a finger
    tick has to address one row and the model has no reason to invent keys.
    Anything else is refused by returning `None` — the caller decides what the
    refusal is called, this module does not raise product errors.
    """
    if raw is None:
        return None
    if not isinstance(raw, list):
        return None
    items: list[ChecklistItem] = []
    for index, row in enumerate(raw):
        if isinstance(row, ChecklistItem):
            items.append(row)
            continue
        if isinstance(row, str):
            text = row.strip()
            if not text:
                return None
            items.append(ChecklistItem(id=f"item-{index + 1}", text=text))
            continue
        if isinstance(row, dict):
            text = str(row.get("text", "")).strip()
            if not text:
                return None
            items.append(
                ChecklistItem(
                    id=str(row.get("id") or f"item-{index + 1}"),
                    text=text,
                    done=bool(row.get("done", False)),
                )
            )
            continue
        return None
    return items


# --- timer ----------------------------------------------------------------


def timer_is_running(payload: WidgetPayload) -> bool:
    """A timer is running exactly while it remembers when it started."""
    return payload.started_at is not None


def timer_elapsed(payload: WidgetPayload, now: datetime) -> int:
    """Seconds spent so far: what was banked plus the run that is going.

    Never negative, and never ahead of the clock. A `started_at` in the future
    — a device whose time moved back, or a snapshot that arrived from the
    server ahead of us — reads as a run that has produced nothing yet, not as
    a debt: elapsed time is arithmetic, and arithmetic does not punish.
    """
    banked = max(0, payload.elapsed or 0)
    started = payload.started_at
    if started is None:
        return banked
    return banked + max(0, int((now - started).total_seconds()))


def timer_remaining(payload: WidgetPayload, now: datetime) -> int:
    """Seconds left of the length the person named. Floored at zero."""
    total = max(0, payload.seconds or 0)
    return max(0, total - timer_elapsed(payload, now))


def timer_is_done(payload: WidgetPayload, now: datetime) -> bool:
    """The named length is spent. A timer with no length never gets there."""
    total = payload.seconds or 0
    return total > 0 and timer_elapsed(payload, now) >= total


def start_timer(payload: WidgetPayload, now: datetime) -> WidgetPayload:
    """Begin, or resume. Starting a running timer is a no-op — pressing start
    twice must not reset the moment it started and lose the minutes."""
    if timer_is_running(payload):
        return payload
    return payload.model_copy(
        update={"started_at": now, "elapsed": max(0, payload.elapsed or 0)}
    )


def pause_timer(payload: WidgetPayload, now: datetime) -> WidgetPayload:
    """Stop the run and bank what it produced. Pausing a stopped timer is a no-op."""
    if not timer_is_running(payload):
        return payload
    return payload.model_copy(
        update={"started_at": None, "elapsed": timer_elapsed(payload, now)}
    )


def reset_timer(payload: WidgetPayload) -> WidgetPayload:
    """Back to the full length. The length itself is not touched."""
    return payload.model_copy(update={"started_at": None, "elapsed": 0})


def build_seconds(raw: object) -> int | None:
    """Read a timer's length off a tool call. Zero and nonsense are not lengths."""
    if isinstance(raw, bool) or raw is None:
        return None
    if not isinstance(raw, (int, float, str)):
        return None
    try:
        seconds = int(raw)
    except (TypeError, ValueError):
        return None
    return seconds if seconds > 0 else None


# --- stepper --------------------------------------------------------------


def stepper_beats(payload: WidgetPayload) -> list[str]:
    """The beats of the sequence. A stepper with none is an empty list."""
    return list(payload.beats or [])


def stepper_position(payload: WidgetPayload) -> int:
    """Where the person is standing, clamped into the list that exists.

    A saved position past the end — the sequence was rewritten shorter — reads
    as the last beat, not as a crash and not as a silent reset to the start.
    """
    beats = stepper_beats(payload)
    if not beats:
        return 0
    return min(max(payload.current or 0, 0), len(beats) - 1)


def stepper_beat(payload: WidgetPayload) -> str | None:
    beats = stepper_beats(payload)
    if not beats:
        return None
    return beats[stepper_position(payload)]


def stepper_is_last(payload: WidgetPayload) -> bool:
    beats = stepper_beats(payload)
    return bool(beats) and stepper_position(payload) == len(beats) - 1


def step_forward(payload: WidgetPayload) -> WidgetPayload:
    """One beat on. The last beat does not roll over into the first — a
    sequence that wraps is a carousel, and this is a thing being done once."""
    beats = stepper_beats(payload)
    if not beats:
        return payload
    return payload.model_copy(
        update={"current": min(stepper_position(payload) + 1, len(beats) - 1)}
    )


def step_back(payload: WidgetPayload) -> WidgetPayload:
    """One beat back. The first beat does not wrap to the end."""
    beats = stepper_beats(payload)
    if not beats:
        return payload
    return payload.model_copy(update={"current": max(0, stepper_position(payload) - 1)})


def build_beats(raw: object) -> list[str] | None:
    """Read beats off a tool call: a list of non-empty lines, or nothing."""
    if raw is None or not isinstance(raw, list):
        return None
    beats: list[str] = []
    for row in raw:
        if not isinstance(row, str):
            return None
        text = row.strip()
        if not text:
            return None
        beats.append(text)
    return beats
