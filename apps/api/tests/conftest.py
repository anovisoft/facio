from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from facio_api.main import app, get_llm
from facio_api.patches import TurnOut
from facio_domain.fixtures import load_cues, load_subjects, load_widgets
from facio_domain.models import Cue, Subject, Widget


@pytest.fixture
def push_ups() -> Subject:
    return next(item for item in load_subjects() if item.id == "push-ups")


@pytest.fixture
def push_cues() -> list[Cue]:
    return [item for item in load_cues() if item.subject_id == "push-ups"]


@pytest.fixture
def push_widget() -> Widget:
    return next(item for item in load_widgets() if item.subject_id == "push-ups")


@pytest.fixture
def turn_body(push_ups: Subject, push_cues: list[Cue], push_widget: Widget) -> dict:
    return {
        "utterance": "",
        "subject": push_ups.model_dump(mode="json"),
        "cues": [cue.model_dump(mode="json") for cue in push_cues],
        "widget": push_widget.model_dump(mode="json"),
    }


class ScriptedLlm:
    def __init__(self, result: TurnOut | Exception) -> None:
        self.result = result
        self.calls: list[dict] = []

    async def generate(self, **kwargs) -> TurnOut:
        self.calls.append(kwargs)
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def override_llm(llm: ScriptedLlm) -> None:
    app.dependency_overrides[get_llm] = lambda: llm
