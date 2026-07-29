import pytest
from pydantic import ValidationError

from app.schemas.create_response import CreateLlmResponse
from tests.factories import sample_create_path, sample_instant_answer


def test_path_branch_valid():
    parsed = CreateLlmResponse.model_validate(sample_create_path())
    assert parsed.kind == "path"
    assert parsed.path is not None
    assert parsed.instant_answer is None


def test_instant_answer_branch_valid():
    parsed = CreateLlmResponse.model_validate(sample_instant_answer())
    assert parsed.kind == "instant_answer"
    assert parsed.instant_answer is not None
    assert len(parsed.instant_answer.goal_suggestions) >= 2


def test_path_requires_path_payload():
    with pytest.raises(ValidationError, match="path is required"):
        CreateLlmResponse.model_validate(
            {"kind": "path", "path": None, "instant_answer": None}
        )


def test_instant_requires_payload():
    with pytest.raises(ValidationError, match="instant_answer is required"):
        CreateLlmResponse.model_validate(
            {"kind": "instant_answer", "path": None, "instant_answer": None}
        )


def test_goal_suggestions_min_two():
    payload = sample_instant_answer()
    payload["instant_answer"]["goal_suggestions"] = ["only one"]
    with pytest.raises(ValidationError):
        CreateLlmResponse.model_validate(payload)
