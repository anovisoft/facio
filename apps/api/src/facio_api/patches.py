"""Narrow talk patches. Surface is required; unvalidated model text is not a payload."""

from __future__ import annotations

from typing import Annotated, Literal, Never

from facio_domain.cues import add_cue
from facio_domain.models import Cadence, CueKind, CueSurface, Subject, Target
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError


class AddCuePatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    op: Literal["add_cue"] = "add_cue"
    kind: CueKind
    text: str
    surface: CueSurface


class SetTargetPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    op: Literal["set_target"] = "set_target"
    current: int | None = None
    goal: int = Field(ge=1)


class SetCadencePatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    op: Literal["set_cadence"] = "set_cadence"
    count: int = Field(ge=1)
    period: Literal["day", "week"]


class ShrinkCadenceSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    count: Literal[1] = 1
    period: Literal["week"] = "week"


class ShrinkPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    op: Literal["shrink"] = "shrink"
    cadence: ShrinkCadenceSpec | Literal["none"] | None = None


class NonePatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    op: Literal["none"] = "none"


Patch = Annotated[
    AddCuePatch | SetTargetPatch | SetCadencePatch | ShrinkPatch | NonePatch,
    Field(discriminator="op"),
]

PATCH_ADAPTER: TypeAdapter[Patch] = TypeAdapter(Patch)


class TurnOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    confirmation: str
    patches: list[Patch]


class LlmPatchWire(BaseModel):
    """Anthropic-friendly flat patch. Empty / -1 means the field was omitted."""

    model_config = ConfigDict(extra="forbid")

    op: Literal["add_cue", "set_target", "set_cadence", "shrink", "none"]
    kind: Literal["correction", "clarification", ""] = ""
    text: str = ""
    surface: Literal["do-time", "on-demand", "timing", "placement", ""] = ""
    current: int = -1
    goal: int = -1
    count: int = -1
    period: Literal["day", "week", ""] = ""
    shrink_cadence: Literal["week", "none", ""] = ""


class LlmTurnWire(BaseModel):
    model_config = ConfigDict(extra="forbid")

    confirmation: str
    patches: list[LlmPatchWire]


class PatchRejected(ValueError):
    """Invalid or forbidden patch. Maps to HTTP 422."""


def parse_patch(data: object) -> Patch:
    try:
        return PATCH_ADAPTER.validate_python(data)
    except ValidationError as exc:
        raise PatchRejected(str(exc)) from exc


def parse_patches(rows: list[object]) -> list[Patch]:
    return [parse_patch(row) for row in rows]


def wire_to_patch(wire: LlmPatchWire) -> Patch:
    match wire.op:
        case "add_cue":
            if not wire.surface:
                raise PatchRejected("add_cue requires surface")
            if not wire.kind or not wire.text.strip():
                raise PatchRejected("add_cue requires kind and text")
            return AddCuePatch(kind=CueKind(wire.kind), text=wire.text, surface=CueSurface(wire.surface))
        case "set_target":
            if wire.goal < 1:
                raise PatchRejected("set_target requires goal >= 1")
            current = None if wire.current < 0 else wire.current
            return SetTargetPatch(current=current, goal=wire.goal)
        case "set_cadence":
            if wire.count < 1 or wire.period not in {"day", "week"}:
                raise PatchRejected("set_cadence requires count >= 1 and period day|week")
            return SetCadencePatch(count=wire.count, period=wire.period)
        case "shrink":
            cadence: ShrinkCadenceSpec | Literal["none"] | None
            if wire.shrink_cadence == "none":
                cadence = "none"
            elif wire.shrink_cadence == "week":
                cadence = ShrinkCadenceSpec()
            else:
                cadence = None
            return ShrinkPatch(cadence=cadence)
        case "none":
            return NonePatch()
        case _:
            unreachable: Never = wire.op
            raise PatchRejected(str(unreachable))


def wire_to_turn(wire: LlmTurnWire) -> TurnOut:
    return TurnOut(confirmation=wire.confirmation, patches=[wire_to_patch(item) for item in wire.patches])


def validate_patches(subject: Subject, patches: list[Patch]) -> None:
    """Reject freeform payload; every mutating op must construct a domain object."""
    for patch in patches:
        match patch:
            case AddCuePatch():
                add_cue(
                    id="preview",
                    subject_id=subject.id,
                    kind=patch.kind,
                    text=patch.text,
                    surface=patch.surface,
                )
            case SetTargetPatch():
                current = patch.current
                if current is None:
                    current = subject.target.current if subject.target else 0
                Target(current=current, goal=patch.goal)
            case SetCadencePatch():
                Cadence.of(patch.count, patch.period)
            case ShrinkPatch():
                if patch.cadence == "none":
                    Cadence.none()
                else:
                    Cadence.of(1, "week")
            case NonePatch():
                pass
            case _:
                unreachable: Never = patch
                raise PatchRejected(str(unreachable))
