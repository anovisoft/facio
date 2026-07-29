import json

import pytest

from app.services.path_llm import (
    messages_for_create,
    messages_for_refine,
    messages_for_repair,
    parse_create_response,
    parse_path_state,
)
from tests.factories import (
    sample_create_path,
    sample_instant_answer,
    sample_path_state,
)


def test_parse_path_from_dict():
    state = parse_path_state(sample_path_state())
    assert state.outcome.startswith("Приготовить")


def test_parse_path_from_json_string():
    state = parse_path_state(json.dumps(sample_path_state(), ensure_ascii=False))
    assert state.domain == "cooking"


def test_parse_create_path():
    parsed = parse_create_response(sample_create_path())
    assert parsed.kind == "path"


def test_parse_create_instant():
    parsed = parse_create_response(sample_instant_answer())
    assert parsed.kind == "instant_answer"


def test_parse_rejects_unknown_type():
    with pytest.raises(TypeError):
        parse_path_state(123)


def test_messages_for_create_include_intent():
    messages = messages_for_create("Приготовить карбонару")
    assert messages[0]["role"] == "system"
    assert "Приготовить карбонару" in messages[-1]["content"]


def test_messages_for_refine_and_repair_shape():
    state = sample_path_state()
    refine = messages_for_refine(
        current_state=state, answer="2", question_id="q_servings"
    )
    assert refine[0]["role"] == "system"
    body = json.loads(refine[1]["content"])
    assert body["answer"] == "2"
    assert body["question_id"] == "q_servings"

    repair = messages_for_repair(
        current_state=state, reason="нет времени", project_status="active"
    )
    repair_body = json.loads(repair[1]["content"])
    assert repair_body["reason"] == "нет времени"
    assert repair_body["project_status"] == "active"
