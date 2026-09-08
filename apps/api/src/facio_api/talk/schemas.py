from datetime import datetime, time
from typing import Annotated, Literal

from facio_domain.models import Desk
from pydantic import BaseModel, Field

Locale = Literal["ru", "en"]


class ThreadMessage(BaseModel):
    role: str
    text: str


class TalkSelection(BaseModel):
    """A phrase the person selected in the assistant's answer, and what it hangs on.

    `quote` is text — never an offset into a message ([04] Cue). The binding is
    whatever the client could name: the widget the sheet was opened from, the
    subject behind it, the step the `?` will sit on. All three may be missing,
    and then the turn owes the person text only: a selection with no bound
    subject produces no cue ([05] «Ask about a phrase, keep the answer»).
    """

    quote: str
    widget_id: str | None = None
    subject_id: str | None = None
    step_id: str | None = None


class TalkTurnRequest(BaseModel):
    utterance: str
    desk: Desk
    thread: list[ThreadMessage] = Field(default_factory=list)
    focused_widget_id: str | None = None
    selection: TalkSelection | None = None
    thread_id: str | None = None
    now: datetime | None = None
    locale: Locale = "ru"


class ToolCallRecord(BaseModel):
    name: str
    arguments: dict
    ok: bool
    error: str | None = None


class CounterFace(BaseModel):
    kind: Literal["counter"] = "counter"
    count: int
    goal: int | None = None


class TickFace(BaseModel):
    kind: Literal["tick"] = "tick"
    done: bool


class ChecklistFace(BaseModel):
    kind: Literal["checklist"] = "checklist"
    done: int
    total: int


class TimerFace(BaseModel):
    kind: Literal["timer"] = "timer"
    seconds: int


class StepperFace(BaseModel):
    kind: Literal["stepper"] = "stepper"
    step: int
    total: int


class ReminderFace(BaseModel):
    kind: Literal["reminder"] = "reminder"
    clock: time | None = None
    closes_at: time | None = None
    skipped: bool = False


class PausedFace(BaseModel):
    """The practice was frozen when the card was written.

    A whole-card state, not a number: the same phrase the client already owns
    (`DisplayCopy.pausedNow`). It used to be spelled out here in Russian and
    win over the translated one.
    """

    kind: Literal["paused"] = "paused"


class BlankFace(BaseModel):
    """Nothing to draw — a stepper with no beats, or a type with no face."""

    kind: Literal["none"] = "none"


SnapshotFace = Annotated[
    CounterFace | TickFace | ChecklistFace | TimerFace | StepperFace | ReminderFace | PausedFace | BlankFace,
    Field(discriminator="kind"),
]


class SnapshotCard(BaseModel):
    """The centered chat card: a picture of a widget at write time.

    The service sends **state**; the client draws the sentence. `line` is the
    finished Russian sentence the first clients read, kept so one of them still
    works — a client that understands `face` must prefer it, because `line`
    ignores `locale` by construction and always will.
    """

    widget_id: str
    subject_id: str
    instance_id: str
    version: int
    title: str
    line: str
    face: SnapshotFace | None = None
    detail: str | None = None


class TalkTurnResponse(BaseModel):
    text: str
    desk: Desk
    mutated: bool
    snapshots: list[SnapshotCard] = Field(default_factory=list)
    tool_calls: list[ToolCallRecord] = Field(default_factory=list)
    thread_id: str | None = None
    # The row above the composer (03 «Reply chips», Q35). Plain strings, and
    # deliberately nothing else: a chip **is** the text the person sends in
    # their own name, so an id, an action or a callback beside it would turn
    # the row into buttons that decide for them ([06] never-do AI #2). Empty is
    # the ordinary case — most turns have nothing to offer — and the default
    # keeps a client written before this field decoding the same response.
    reply_chips: list[str] = Field(default_factory=list)
