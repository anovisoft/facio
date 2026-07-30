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


def test_parse_path_normalizes_wire_sentinels():
    payload = sample_path_state()
    action = payload["actions"][0]
    action["id"] = ""
    action["detail"] = ""
    action["group_id"] = ""
    action["estimate_min"] = -1
    action["sort"] = -1
    payload["cycle"]["goal_for_cycle"] = ""
    payload["days"][0]["title"] = ""
    payload["days"][0]["summary"] = ""
    payload["groups"][0]["description"] = ""

    state = parse_path_state(payload)
    assert state.actions[0].id is None
    assert state.actions[0].detail is None
    assert state.actions[0].group_id is None
    assert state.actions[0].estimate_min is None
    assert state.actions[0].sort is None
    assert state.cycle.goal_for_cycle is None
    assert state.days[0].title is None
    assert state.days[0].summary is None
    assert state.groups[0].description is None


def test_parse_create_drops_unused_branch_stubs():
    from app.services.path_llm import _EMPTY_INSTANT_STUB, _EMPTY_PATH_STUB

    path_payload = sample_create_path()
    path_payload["instant_answer"] = dict(_EMPTY_INSTANT_STUB)
    parsed_path = parse_create_response(path_payload)
    assert parsed_path.kind == "path"
    assert parsed_path.path is not None
    assert parsed_path.instant_answer is None

    ia_payload = sample_instant_answer()
    ia_payload["path"] = dict(_EMPTY_PATH_STUB)
    parsed_ia = parse_create_response(ia_payload)
    assert parsed_ia.kind == "instant_answer"
    assert parsed_ia.path is None
    assert parsed_ia.instant_answer is not None


def test_parse_rejects_unknown_type():
    with pytest.raises(TypeError):
        parse_path_state(123)


def test_messages_for_create_include_intent():
    messages = messages_for_create("Приготовить карбонару")
    assert messages[0]["role"] == "system"
    assert "Приготовить карбонару" in messages[-1]["content"]
    # Carbonara + push-ups fewshots + instant_answer + final intent
    assert any("30 отжиманий" in m["content"] for m in messages if m["role"] == "user")
    assert "cycle" in messages[0]["content"]
    assert "days[]" in messages[0]["content"]


def test_messages_for_refine_and_repair_shape():
    state = sample_path_state()
    refine = messages_for_refine(
        current_state=state,
        answers=[
            {"question_id": "q_servings", "value": "2"},
            {"question_id": "q_guanciale", "value": "гуанчиале"},
        ],
        comment="без чеснока",
    )
    assert refine[0]["role"] == "system"
    body = json.loads(refine[1]["content"])
    assert body["answers"] == [
        {"question_id": "q_servings", "value": "2"},
        {"question_id": "q_guanciale", "value": "гуанчиале"},
    ]
    assert body["comment"] == "без чеснока"

    repair = messages_for_repair(
        current_state=state, reason="нет времени", project_status="active"
    )
    repair_body = json.loads(repair[1]["content"])
    assert repair_body["reason"] == "нет времени"
    assert repair_body["project_status"] == "active"
