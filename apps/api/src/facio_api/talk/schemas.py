from datetime import datetime
from typing import Literal

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


class SnapshotCard(BaseModel):
    widget_id: str
    subject_id: str
    instance_id: str
    version: int
    title: str
    line: str


class TalkTurnResponse(BaseModel):
    text: str
    desk: Desk
    mutated: bool
    snapshots: list[SnapshotCard] = Field(default_factory=list)
    tool_calls: list[ToolCallRecord] = Field(default_factory=list)
    thread_id: str | None = None
