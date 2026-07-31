import pytest
from pydantic import ValidationError

from app.schemas.path_state import PathState
from tests.factories import sample_path_state


def test_valid_path_state():
    state = PathState.model_validate(sample_path_state())
    assert state.title
    assert state.summary
    assert state.outcome
    assert state.domain == "cooking"
    assert len(state.actions) == 2
    assert all(a.why.strip() for a in state.actions)


def test_empty_why_rejected():
    payload = sample_path_state()
    payload["actions"][0]["why"] = "   "
    with pytest.raises(ValidationError, match="why"):
        PathState.model_validate(payload)


def test_single_question_rejected():
    payload = sample_path_state()
    payload["questions"] = [
        {"id": "q1", "prompt": "Only one?", "options": ["a"]},
    ]
    with pytest.raises(ValidationError, match="2–4"):
        PathState.model_validate(payload)


def test_empty_questions_ok():
    state = PathState.model_validate(sample_path_state(questions=[]))
    assert state.questions == []


def test_unknown_group_id_rejected():
    payload = sample_path_state()
    payload["actions"][0]["group_id"] = "missing"
    with pytest.raises(ValidationError, match="group_id"):
        PathState.model_validate(payload)


def test_tags_normalized_and_deduped():
    payload = sample_path_state(
        tags=[" Pasta ", "pasta", "Dinner", "Extra Tag"]
    )
    state = PathState.model_validate(payload)
    assert state.tags == ["pasta", "dinner", "extra-tag"]


def test_tags_max_five_rejected():
    payload = sample_path_state(
        tags=["a", "b", "c", "d", "e", "f"]
    )
    with pytest.raises(ValidationError):
        PathState.model_validate(payload)


def test_invalid_domain_rejected():
    payload = sample_path_state(domain="spaceships")
    with pytest.raises(ValidationError):
        PathState.model_validate(payload)


def test_empty_actions_allowed_for_progressive_start():
    """Phase-1 start surface may persist with actions=[] (path_ready=false)."""
    payload = sample_path_state(actions=[])
    state = PathState.model_validate(payload)
    assert state.actions == []


def test_missing_title_summary_backfilled_from_contract():
    payload = sample_path_state()
    del payload["title"]
    del payload["summary"]
    state = PathState.model_validate(payload)
    assert state.title == payload["outcome"]
    assert state.summary == payload["success_criteria"]


def test_empty_title_rejected():
    payload = sample_path_state(title="   ")
    with pytest.raises(ValidationError):
        PathState.model_validate(payload)


def test_group_description_optional():
    state = PathState.model_validate(sample_path_state())
    assert state.groups[0].description
    payload = sample_path_state()
    payload["groups"][0]["description"] = None
    cleared = PathState.model_validate(payload)
    assert cleared.groups[0].description is None


def test_cycle_and_days_present():
    state = PathState.model_validate(sample_path_state())
    assert state.cycle.horizon_days == 1
    assert state.cycle.status == "draft"
    assert len(state.days) == 1
    assert state.days[0].kind == "cook_session"


def test_cycle_days_backfilled_from_legacy_payload():
    payload = sample_path_state()
    del payload["cycle"]
    del payload["days"]
    state = PathState.model_validate(payload)
    assert state.cycle.horizon_days == 1
    assert state.days[0].kind == "cook_session"
    assert state.days[0].day_index == 0


def test_fitness_week_has_train_and_rest():
    from tests.factories import sample_fitness_path_state

    state = PathState.model_validate(sample_fitness_path_state())
    assert state.cycle.horizon_days == 7
    kinds = {d.kind for d in state.days}
    assert "train" in kinds
    assert "rest" in kinds
    assert len(state.days) == 7


def test_action_day_offset_must_match_day():
    payload = sample_path_state()
    payload["actions"][0]["day_offset"] = 3
    with pytest.raises(ValidationError, match="day_offset"):
        PathState.model_validate(payload)


def test_duplicate_day_index_rejected():
    payload = sample_path_state()
    payload["days"] = [
        {"day_index": 0, "kind": "cook_session"},
        {"day_index": 0, "kind": "other"},
    ]
    with pytest.raises(ValidationError, match="day_index"):
        PathState.model_validate(payload)
