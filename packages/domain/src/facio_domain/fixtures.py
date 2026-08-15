"""Load founder JSON fixtures from packages/domain/fixtures/."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from facio_domain.models import Cue, Instance, Subject, Widget


def fixtures_dir() -> Path:
    """packages/domain/fixtures — shared with the future client."""
    here = Path(__file__).resolve()
    candidate = here.parents[2] / "fixtures"
    if not candidate.is_dir():
        raise FileNotFoundError(f"fixtures directory not found: {candidate}")
    return candidate


def _read(name: str) -> Any:
    path = fixtures_dir() / name
    return json.loads(path.read_text(encoding="utf-8"))


def load_subjects() -> list[Subject]:
    return [Subject.model_validate(row) for row in _read("subjects.json")]


def load_cues() -> list[Cue]:
    return [Cue.model_validate(row) for row in _read("cues.json")]


def load_widgets() -> list[Widget]:
    return [Widget.model_validate(row) for row in _read("widgets.json")]


def load_scenarios() -> dict[str, Any]:
    return _read("scenarios.json")


def subject_by_id(subject_id: str, subjects: list[Subject] | None = None) -> Subject:
    pool = subjects if subjects is not None else load_subjects()
    for subject in pool:
        if subject.id == subject_id:
            return subject
    raise KeyError(subject_id)


def instances_from_rows(rows: list[dict[str, Any]]) -> list[Instance]:
    return [Instance.model_validate(row) for row in rows]
