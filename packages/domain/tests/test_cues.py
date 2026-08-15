from __future__ import annotations

from facio_domain.cues import add_cue, default_surface
from facio_domain.models import CueKind, CueSurface, LinkMedia


def test_correction_defaults_to_do_time() -> None:
    assert default_surface(CueKind.correction) == CueSurface.do_time
    cue = add_cue(
        id="c1",
        subject_id="push-ups",
        kind="correction",
        text="brace the core and the glutes",
    )
    assert cue.surface == CueSurface.do_time


def test_clarification_defaults_to_on_demand() -> None:
    assert default_surface(CueKind.clarification) == CueSurface.on_demand
    cue = add_cue(
        id="c2",
        subject_id="push-ups",
        kind="clarification",
        text="what a hinge is",
        quote="hinge",
    )
    assert cue.surface == CueSurface.on_demand
    assert cue.quote == "hinge"


def test_add_cue_keeps_explicit_surface() -> None:
    cue = add_cue(
        id="c3",
        subject_id="bike",
        kind="correction",
        text="зал до 22",
        surface="timing",
    )
    assert cue.surface == CueSurface.timing


def test_media_is_at_most_one() -> None:
    cue = add_cue(
        id="c4",
        subject_id="push-ups",
        kind="clarification",
        text="the machine",
        media=LinkMedia(url="https://example.com/form"),
    )
    assert cue.media is not None
    assert cue.media.kind == "link"
