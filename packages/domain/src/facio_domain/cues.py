"""Cue construction. Surface is mandatory; kind supplies a default when omitted."""

from __future__ import annotations

from typing import Never

from facio_domain.models import (
    Cue,
    CueHits,
    CueKind,
    CueMedia,
    CueOrigin,
    CueSurface,
)


def default_surface(kind: CueKind) -> CueSurface:
    """correction → do-time; clarification → on-demand."""
    match kind:
        case CueKind.correction:
            return CueSurface.do_time
        case CueKind.clarification:
            return CueSurface.on_demand
        case _:
            unreachable: Never = kind
            raise ValueError(unreachable)


def add_cue(
    *,
    id: str,
    subject_id: str,
    kind: CueKind | str,
    text: str,
    surface: CueSurface | str | None = None,
    step_id: str | None = None,
    quote: str | None = None,
    media: CueMedia | None = None,
    origin: CueOrigin | None = None,
    hits: CueHits | None = None,
) -> Cue:
    """Build a cue. Missing surface uses the kind default; Cue still requires one.

    Raw `Cue(...)` without `surface` fails validation — a fact with nowhere
    to appear is not a cue.
    """
    parsed_kind = kind if isinstance(kind, CueKind) else CueKind(kind)
    if surface is None:
        parsed_surface = default_surface(parsed_kind)
    elif isinstance(surface, CueSurface):
        parsed_surface = surface
    else:
        parsed_surface = CueSurface(surface)
    return Cue(
        id=id,
        subject_id=subject_id,
        step_id=step_id,
        kind=parsed_kind,
        text=text,
        quote=quote,
        media=media,
        origin=origin,
        surface=parsed_surface,
        hits=hits or CueHits(),
    )
