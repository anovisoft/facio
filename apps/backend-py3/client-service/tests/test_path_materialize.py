"""Unit tests for ensure_action_keys / apply_contract helpers."""

from uuid import uuid4

from app.models import Project, ProjectStatus
from app.schemas.path_state import PathState
from app.services.path_materialize import apply_contract, ensure_action_keys
from tests.factories import sample_path_state


def test_ensure_action_keys_fills_missing_ids():
    payload = sample_path_state()
    payload["actions"][0]["id"] = None
    payload["actions"][0]["checklist_items"][0]["id"] = None
    state = ensure_action_keys(PathState.model_validate(payload))
    assert state.actions[0].id == "a0"
    assert state.actions[0].checklist_items[0].id == "c0"
    assert state.actions[1].id == "cook"


def test_apply_contract_copies_fields():
    project = Project(
        id=uuid4(),
        user_id=uuid4(),
        status=ProjectStatus.draft,
        raw_intent="x",
    )
    state = PathState.model_validate(sample_path_state())
    apply_contract(project, state)
    assert project.outcome == state.outcome
    assert project.paraphrase == state.paraphrase
    assert project.title == state.title
    assert project.summary == state.summary
    assert project.domain == state.domain
    assert project.tags == list(state.tags)
