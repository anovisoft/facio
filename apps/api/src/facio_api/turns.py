"""One turn: focused subject + cues + widget + utterance → validated patches."""

from __future__ import annotations

from typing import Any

from facio_domain.models import Cue, Subject, Widget
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from facio_api.llm import TurnGenerator
from facio_api.patches import PatchRejected, TurnOut, validate_patches
from facio_api.policy import apply_pain_policy


class TurnIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    utterance: str = Field(min_length=1)
    subject: dict[str, Any]
    cues: list[dict[str, Any]]
    widget: dict[str, Any]


def _take(model: type[BaseModel], data: dict[str, Any]) -> dict[str, Any]:
    return {key: data[key] for key in model.model_fields if key in data}


def parse_subject(data: dict[str, Any]) -> Subject:
    try:
        return Subject.model_validate(_take(Subject, data))
    except ValidationError as exc:
        raise PatchRejected(f"invalid subject: {exc}") from exc


def parse_cues(rows: list[dict[str, Any]]) -> list[Cue]:
    try:
        return [Cue.model_validate(_take(Cue, row)) for row in rows]
    except ValidationError as exc:
        raise PatchRejected(f"invalid cue: {exc}") from exc


def parse_widget(data: dict[str, Any]) -> Widget:
    try:
        return Widget.model_validate(_take(Widget, data))
    except ValidationError as exc:
        raise PatchRejected(f"invalid widget: {exc}") from exc


async def run_turn(body: TurnIn, llm: TurnGenerator) -> TurnOut:
    subject = parse_subject(body.subject)
    cues = parse_cues(body.cues)
    widget = parse_widget(body.widget)
    result = await llm.generate(
        utterance=body.utterance,
        subject=subject,
        cues=cues,
        widget=widget,
    )
    patches = apply_pain_policy(body.utterance, subject, result.patches)
    validate_patches(subject, patches)
    return TurnOut(confirmation=result.confirmation, patches=patches)
