from __future__ import annotations

import pytest
from pydantic import ValidationError

from facio_domain.models import Cadence, Cue, CueKind, Subject, SubjectStatus
from facio_domain.subjects import retire_subject, shrink_subject


def test_subject_has_no_stored_drift(push_ups: Subject) -> None:
    assert "drift" not in Subject.model_fields
    assert not hasattr(push_ups, "drift")


def test_push_ups_fixture(push_ups: Subject, cues) -> None:
    assert push_ups.cadence.count == 3
    assert push_ups.cadence.period == "week"
    assert push_ups.target is not None
    assert push_ups.target.current == 28
    assert push_ups.target.goal == 30
    brace = next(cue for cue in cues if cue.id == "push-ups-brace")
    assert brace.kind == CueKind.correction
    assert brace.surface == "do-time"
    assert brace.text == "brace the core and the glutes"
    assert "push-ups-brace" in push_ups.cue_ids


def test_bike_fixture(bike: Subject, cues) -> None:
    assert bike.cadence.count == 2
    assert bike.cadence.period == "week"
    assert bike.window is not None
    assert bike.window.closes_at.hour == 22
    assert bike.window.latest_by.hour == 19
    timing = next(cue for cue in cues if cue.id == "bike-gym-hours")
    assert timing.surface == "timing"
    assert timing.text == "зал до 22"


def test_vegetables_is_daily_ish(vegetables: Subject) -> None:
    assert vegetables.cadence.count == 1
    assert vegetables.cadence.period == "day"


def test_cadence_none_rejects_count() -> None:
    with pytest.raises(ValidationError):
        Cadence(count=1, period="none")


def test_cadence_count_requires_count() -> None:
    with pytest.raises(ValidationError):
        Cadence(period="week")


def test_cue_without_surface_fails() -> None:
    with pytest.raises(ValidationError):
        Cue(
            id="orphan",
            subject_id="push-ups",
            kind="correction",
            text="brace the core and the glutes",
        )


def test_quote_is_text_not_offset() -> None:
    with pytest.raises(ValidationError):
        Cue(
            id="bad-quote",
            subject_id="push-ups",
            kind="clarification",
            text="what this means",
            quote=14,
            surface="on-demand",
        )


def test_retire_and_shrink_keep_instances_and_cues(push_ups: Subject) -> None:
    marked = push_ups.model_copy(
        update={"instance_ids": ["a"], "cue_ids": ["push-ups-brace"]}
    )
    shrunk = shrink_subject(marked)
    retired = retire_subject(marked)
    assert shrunk.status == SubjectStatus.shrunk
    assert retired.status == SubjectStatus.retired
    assert shrunk.instance_ids == marked.instance_ids
    assert retired.instance_ids == marked.instance_ids
    assert shrunk.cue_ids == marked.cue_ids
    assert retired.cue_ids == marked.cue_ids
