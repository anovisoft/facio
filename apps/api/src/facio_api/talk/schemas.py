from datetime import datetime
from typing import Literal

from facio_domain.models import Desk
from pydantic import BaseModel, Field

Locale = Literal["ru", "en"]


class ThreadMessage(BaseModel):
    role: str
    text: str


class TalkTurnRequest(BaseModel):
    utterance: str
    desk: Desk
    thread: list[ThreadMessage] = Field(default_factory=list)
    focused_widget_id: str | None = None
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
