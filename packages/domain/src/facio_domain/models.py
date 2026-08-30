"""Pydantic models for the Facio domain law.

Field names match docs/rfc/04-domain-model.md. Drift is not a stored field.
"""

from __future__ import annotations

from datetime import datetime, time
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class SubjectStatus(StrEnum):
    active = "active"
    shrunk = "shrunk"
    paused = "paused"
    retired = "retired"


class CueKind(StrEnum):
    correction = "correction"
    clarification = "clarification"


class CueSurface(StrEnum):
    do_time = "do-time"
    on_demand = "on-demand"
    timing = "timing"
    placement = "placement"


class InstanceStatus(StrEnum):
    completed = "completed"
    prepared = "prepared"
    in_progress = "in_progress"


class WidgetType(StrEnum):
    counter = "counter"
    tick = "tick"
    checklist = "checklist"
    reminder = "reminder"
    timer = "timer"
    stepper = "stepper"


class WidgetStatus(StrEnum):
    ready = "ready"
    running = "running"
    done = "done"
    skipped = "skipped"
    snoozed = "snoozed"
    archived = "archived"


class WidgetSection(StrEnum):
    today = "today"
    lifetime = "lifetime"
    soon = "soon"
    postponed = "postponed"


class DriftOffer(StrEnum):
    move_to_today = "move_to_today"
    once_a_week = "once_a_week"
    retire = "retire"
    stop = "stop"


class RankBand(StrEnum):
    in_progress = "in_progress"
    overdue = "overdue"
    unanswered_morning = "unanswered_morning"
    drift_card = "drift_card"
    soon_by_time = "soon_by_time"
    today_incomplete = "today_incomplete"
    today_done = "today_done"


class Cadence(BaseModel):
    """Count per period, or `none` (one-off).

    This is a count over a period, not fixed weekdays (Q26).
    Daily-ish is modelled as count=1, period=day — no extra flag.
    """

    model_config = ConfigDict(extra="forbid")

    count: int | None = None
    period: Literal["day", "week", "none"] = "none"

    @model_validator(mode="after")
    def _shape(self) -> Cadence:
        if self.period == "none":
            if self.count is not None:
                raise ValueError("cadence none cannot carry a count")
            return self
        if self.count is None or self.count < 1:
            raise ValueError("count cadence needs count >= 1")
        return self

    @classmethod
    def of(cls, count: int, period: Literal["day", "week"]) -> Cadence:
        return cls(count=count, period=period)

    @classmethod
    def none(cls) -> Cadence:
        return cls(period="none")

    @property
    def is_none(self) -> bool:
        return self.period == "none"


class Window(BaseModel):
    """When the practice can still happen.

    `hours` are the stated hours, ordered and without repeats — one window may
    hold several ([07](../../../docs/rfc/07-open-questions.md) Q34): «в 10, 12,
    15, 16:30, 18, 21, 22» is one practice firing seven times, not seven events
    with lives of their own. Nothing invents an hour nobody said.

    `latest_by` is the first of them, kept as a real field so a desk and a wire
    written before Q34 still open and still read: one hour is a legal window and
    always was.

    `closes_at` is the optional source fact (gym door). If no hour was stated,
    latest_by = closes_at minus 3 hours (22:00 → 19:00). A stated hour wins; do
    not replace 19:00 with 23:00 − 3h = 20:00.
    """

    model_config = ConfigDict(extra="forbid")

    hours: list[time] = Field(default_factory=list)
    latest_by: time | None = None
    closes_at: time | None = None

    @model_validator(mode="after")
    def _shape(self) -> Window:
        stated = list(self.hours)
        if self.latest_by is not None and self.latest_by not in stated:
            stated.append(self.latest_by)
        if not stated:
            raise ValueError("a window needs at least one stated hour")
        ordered = sorted(set(stated))
        self.hours = ordered
        self.latest_by = ordered[0]
        return self

    @classmethod
    def at(cls, *hours: time, closes_at: time | None = None) -> Window:
        return cls(hours=list(hours), closes_at=closes_at)

    def next_hour(self, after: time) -> time:
        """The nearest hour still ahead, or the first one when the day is spent.

        Used for the one hour a face can show; the alarms still stand on all of
        them.
        """
        return next((hour for hour in self.hours if hour >= after), self.hours[0])


class Target(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current: int
    goal: int


class Subject(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    cadence: Cadence
    window: Window | None = None
    cue_ids: list[str] = Field(default_factory=list)
    target: Target | None = None
    instance_ids: list[str] = Field(default_factory=list)
    status: SubjectStatus = SubjectStatus.active
    paused_at: datetime | None = None
    # The shrink ladder (Q28) remembered on the practice itself, next to the
    # pause. Not a score and not a streak (P7): three plain counters the law
    # reads to decide which rung is next and whether it may speak at all.
    # `drift_asks_made` — how many times this subject was asked, ever.
    # `drift_retire_refusals` — how many times the offer to retire was refused.
    # `drift_asked_at` — when the last ask happened, so the next one waits a
    # full cadence period.
    drift_asks_made: int = Field(default=0, ge=0)
    drift_retire_refusals: int = Field(default=0, ge=0)
    drift_asked_at: datetime | None = None


class PhotoMedia(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["photo"] = "photo"
    ref: str


class LinkMedia(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["link"] = "link"
    url: str


CueMedia = PhotoMedia | LinkMedia


class CueOrigin(BaseModel):
    model_config = ConfigDict(extra="allow")

    chat_id: str | None = None
    message_id: str | None = None


class CueHits(BaseModel):
    model_config = ConfigDict(extra="forbid")

    surfaced: int = Field(default=0, ge=0)
    applied: int = Field(default=0, ge=0)


class Cue(BaseModel):
    """A fact bound to a subject and to a place it appears.

    `surface` is required. A fact with nowhere to show is not a cue.
    `quote` is the selected phrase as text, never an offset into a message.
    """

    model_config = ConfigDict(extra="forbid")

    id: str
    subject_id: str
    step_id: str | None = None
    kind: CueKind
    text: str
    quote: str | None = None
    media: CueMedia | None = None
    origin: CueOrigin | None = None
    surface: CueSurface
    hits: CueHits = Field(default_factory=CueHits)

    @field_validator("quote", mode="before")
    @classmethod
    def quote_is_text(cls, value: object) -> object:
        if value is None:
            return value
        if not isinstance(value, str):
            raise ValueError("quote is stored as text, not an offset")
        return value


class Instance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    subject_id: str
    when: datetime
    status: InstanceStatus


class ChecklistItem(BaseModel):
    """One line of a checklist.

    `done` is finger state on that line, nothing more: no per-item timestamp,
    no score. Progress over the list is arithmetic in `runtime.py`, so the
    payload never carries a "progress" number of its own — a stored count and
    a list of ticks are two truths about the same thing, and they drift.
    """

    model_config = ConfigDict(extra="forbid")

    id: str
    text: str
    done: bool = False


class WidgetPayload(BaseModel):
    """What a runtime needs to run. Extra keys still pass through.

    The typed part is the catalog (Q1): `count`/`target` for the counter,
    `done` for the tick, `fire_at` for the reminder, `items` for the checklist,
    `seconds`/`started_at`/`elapsed` for the timer, `beats`/`current` for the
    stepper. Anything the model invents on top stays in `extra` and no runtime
    reads it (never-do AI #1).
    """

    model_config = ConfigDict(extra="allow")

    count: int | None = None
    target: int | None = None
    done: bool | None = None
    items: list[ChecklistItem] | None = None
    # The length the person named, and the run itself. `started_at` is the
    # moment the current run began — «идёт с момента» — and is empty when the
    # timer is standing still; `elapsed` is what was banked before it.
    # Elapsed time is derived from those two and `now`, never stored ticking.
    seconds: int | None = None
    started_at: datetime | None = None
    elapsed: int | None = None
    # Beats of a stepper and the one the person is standing on (0-based).
    beats: list[str] | None = None
    current: int | None = None
    fire_at: datetime | None = None


class Widget(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    type: WidgetType
    title: str
    payload: WidgetPayload = Field(default_factory=WidgetPayload)
    status: WidgetStatus
    when: datetime | None = None
    section: WidgetSection
    group_id: str | None = None
    subject_id: str
    instance_id: str
    tile_size: str | None = None
    version: int = 1


class DriftCard(BaseModel):
    """The one drift ask on Today. `offer` is the ladder rung the law chose."""

    model_config = ConfigDict(extra="forbid")

    subject_id: str
    silent_days: int
    offer: DriftOffer


class DeltaCard(BaseModel):
    """The calm half of the morning (Q6): promised by the rhythm minus done.

    No offer and no chips — a delta without drift is a statement, not an
    accusation (P7). `remaining` is never negative: doing more than promised
    is not a debt.
    """

    model_config = ConfigDict(extra="forbid")

    subject_id: str
    promised: int
    done: int
    remaining: int


class WidgetTodayItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["widget"] = "widget"
    band: RankBand
    widget: Widget


class DriftTodayItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["drift"] = "drift"
    band: Literal[RankBand.drift_card] = RankBand.drift_card
    drift_card: DriftCard


class DeltaTodayItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["delta"] = "delta"
    band: Literal[RankBand.unanswered_morning] = RankBand.unanswered_morning
    delta_card: DeltaCard


TodayItem = WidgetTodayItem | DriftTodayItem | DeltaTodayItem


class LidProjection(BaseModel):
    """The lid is a view of what is due now, not a second inventory."""

    model_config = ConfigDict(extra="forbid")

    today: list[TodayItem]
    lifetime: list[Widget]
    soon: list[Widget]
    postponed: list[Widget]
    drift_card: DriftCard | None = None
    delta_card: DeltaCard | None = None


class Desk(BaseModel):
    """The whole table the talk service reads and patches.

    Drift is still derived, never stored. The shrink-ladder memory rides on
    each `Subject` (next to `paused_at`), not in a side table on the desk.
    """

    model_config = ConfigDict(extra="forbid")

    subjects: list[Subject]
    cues: list[Cue]
    instances: list[Instance]
    widgets: list[Widget]
