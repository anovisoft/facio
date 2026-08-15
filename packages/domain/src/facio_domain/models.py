"""Pydantic models for the Facio domain law.

Field names match docs/rfc/04-domain-model.md. Drift is not a stored field.
"""

from __future__ import annotations

from datetime import datetime, time
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class SubjectStatus(StrEnum):
    active = "active"
    shrunk = "shrunk"
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

    `latest_by` is the clock hour the reminder fires.
    `closes_at` is the optional source fact (gym door). Founding rule:
    latest_by = closes_at minus 3 hours (22:00 → 19:00).
    """

    model_config = ConfigDict(extra="forbid")

    latest_by: time
    closes_at: time | None = None


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


class WidgetPayload(BaseModel):
    """Flexible payload; fields used by tests are typed, the rest may pass through."""

    model_config = ConfigDict(extra="allow")

    count: int | None = None
    target: int | None = None
    done: bool | None = None
    items: list[Any] | None = None
    seconds: int | None = None
    elapsed: int | None = None
    steps: list[str] | None = None
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


class DriftAskState(BaseModel):
    """How far the shrink ladder has already been walked for one subject.

    Not a stored score. Input to `next_drift_offer` / `drift_card`.
    """

    model_config = ConfigDict(extra="forbid")

    asks_made: int = Field(default=0, ge=0)
    retire_refusals: int = Field(default=0, ge=0)


class DriftCard(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject_id: str
    silent_days: int
    offer: DriftOffer


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


TodayItem = WidgetTodayItem | DriftTodayItem


class LidProjection(BaseModel):
    """The lid is a view of what is due now, not a second inventory."""

    model_config = ConfigDict(extra="forbid")

    today: list[TodayItem]
    lifetime: list[Widget]
    soon: list[Widget]
    postponed: list[Widget]
    drift_card: DriftCard | None = None
