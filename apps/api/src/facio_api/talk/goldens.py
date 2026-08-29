from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

import facio_api


class ScriptedToolCall(BaseModel):
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class ScriptedTurn(BaseModel):
    text: str | None = None
    tool_calls: list[ScriptedToolCall] = Field(default_factory=list)


class GoldenExpectCue(BaseModel):
    """`kind` is not decoration: a conclusion about *how* to do the thing is a
    correction seen at do-time, an explanation is a clarification behind a `?`
    ([04] Cue). The live model reached for `clarification` on a method."""

    subject_id: str
    surface: str
    kind: str | None = None
    text_contains: list[str] = Field(default_factory=list)


class GoldenExpectCadence(BaseModel):
    """The rhythm the turn must put on the subject it creates.

    A practice with no rhythm is a planner line, not a practice ([06] #14), so a
    golden that places one says what the rhythm is — including `none` for a
    one-off, which is legal but has to be named.
    """

    period: str
    count: int | None = None


class GoldenExpect(BaseModel):
    mutated: bool
    tools: list[str] = Field(default_factory=list)
    cadence: GoldenExpectCadence | None = None
    snapshots_empty: bool | None = None
    target_goal_max: int | None = None
    target_current: int | None = None
    times_per_week_max: float | None = None
    forbidden_tools: list[str] = Field(default_factory=list)
    cue: GoldenExpectCue | None = None


class Golden(BaseModel):
    id: str
    utterance: str
    match: list[str] = Field(default_factory=list)
    scripted: list[ScriptedTurn]
    expect: GoldenExpect


def goldens_dir() -> Path:
    override = os.environ.get("FACIO_GOLDENS_DIR")
    if override:
        return Path(override)
    return Path(facio_api.__file__).resolve().parents[2] / "goldens"


def load_goldens() -> list[Golden]:
    rows: list[Golden] = []
    for path in sorted(goldens_dir().glob("*.json")):
        rows.append(Golden.model_validate(json.loads(path.read_text(encoding="utf-8"))))
    return rows


def match_golden(utterance: str, goldens: list[Golden] | None = None) -> Golden | None:
    text = utterance.casefold()
    for golden in goldens or load_goldens():
        needles = golden.match or [golden.utterance]
        if any(needle.casefold() in text for needle in needles):
            return golden
    return None
