from __future__ import annotations

from datetime import datetime

import pytest

from facio_domain.fixtures import load_cues, load_scenarios, load_subjects, load_widgets
from facio_domain.models import Cue, Subject, Widget


@pytest.fixture
def subjects() -> list[Subject]:
    return load_subjects()


@pytest.fixture
def cues() -> list[Cue]:
    return load_cues()


@pytest.fixture
def widgets() -> list[Widget]:
    return load_widgets()


@pytest.fixture
def scenarios() -> dict:
    return load_scenarios()


@pytest.fixture
def now(scenarios: dict) -> datetime:
    return datetime.fromisoformat(scenarios["now"])


@pytest.fixture
def push_ups(subjects: list[Subject]) -> Subject:
    return next(subject for subject in subjects if subject.id == "push-ups")


@pytest.fixture
def bike(subjects: list[Subject]) -> Subject:
    return next(subject for subject in subjects if subject.id == "bike")


@pytest.fixture
def vegetables(subjects: list[Subject]) -> Subject:
    return next(subject for subject in subjects if subject.id == "vegetables")
