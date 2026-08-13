import json

import pytest

from app.services.path_llm import (
    messages_for_create,
    messages_for_create_gate,
    messages_for_create_path,
    messages_for_refine,
    messages_for_repair,
    parse_create_gate,
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
    cook = payload["actions"][2]
    cook["counter"] = {
        "label": "",
        "target": -1,
        "current": 0,
        "step": 1,
    }
    cook["timeline"] = {"duration_sec": -1, "markers": []}
    cook["interval_plan"] = {"segments": []}
    cook["timers"] = [
        {
            "id": "",
            "title": "Лапша",
            "duration_sec": 60,
            "signal": "alert",
            "parallel_group": "",
        }
    ]

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
    assert state.actions[2].counter is None
    assert state.actions[2].timeline is None
    assert state.actions[2].interval_plan is None
    assert len(state.actions[2].timers) == 1
    assert state.actions[2].timers[0].id is None
    assert state.actions[2].timers[0].parallel_group is None


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


def test_parse_create_gate_path():
    parsed = parse_create_gate(
        {
            "kind": "path",
            "instant_answer": {
                "label": "",
                "answer": "",
                "goal_suggestions": [],
                "domain": "other",
            },
            "path_start": {
                "paraphrase": "Ок — ведём к: карбонара",
                "title": "Карбонара",
                "summary": "Купим и приготовим за вечер.",
                "questions": [
                    {
                        "id": "meat",
                        "prompt": "Какое мясо?",
                        "options": ["гуанчиале", "панчетта"],
                    },
                    {
                        "id": "servings",
                        "prompt": "Порций?",
                        "options": ["1", "2"],
                    },
                ],
                "outline_days": ["Вечер готовки"],
            },
        }
    )
    assert parsed.kind == "path"
    assert parsed.instant_answer is None
    assert parsed.path_start is not None
    assert parsed.path_start.title == "Карбонара"


def test_parse_create_gate_path_requires_start():
    with pytest.raises(ValueError, match="path_start"):
        parse_create_gate(
            {
                "kind": "path",
                "instant_answer": {
                    "label": "",
                    "answer": "",
                    "goal_suggestions": [],
                    "domain": "other",
                },
            }
        )


def test_parse_create_gate_instant():
    ia = sample_instant_answer()["instant_answer"]
    parsed = parse_create_gate(
        {
            "kind": "instant_answer",
            "instant_answer": ia,
            "path_start": {
                "paraphrase": "",
                "title": "",
                "summary": "",
                "questions": [],
                "outline_days": [],
            },
        }
    )
    assert parsed.kind == "instant_answer"
    assert parsed.instant_answer is not None
    assert len(parsed.instant_answer.goal_suggestions) >= 2
    assert parsed.path_start is None


def test_messages_for_create_include_intent():
    gate = messages_for_create_gate("Приготовить карбонару")
    assert gate[0]["role"] == "system"
    assert "Приготовить карбонару" in gate[-1]["content"]
    assert "Gate" in gate[0]["content"] or "sequence" in gate[0]["content"].lower()
    # Alias still works
    assert messages_for_create("x")[-1]["content"] == "x"

    path_msgs = messages_for_create_path("Приготовить карбонару")
    assert path_msgs[0]["role"] == "system"
    assert "cycle" in path_msgs[0]["content"]
    assert "days[]" in path_msgs[0]["content"]
    assert any("30 отжиманий" in m["content"] for m in path_msgs if m["role"] == "user")
    # Path few-shots are Path JSON roots (no kind wrapper).
    assistant = json.loads(
        next(m["content"] for m in path_msgs if m["role"] == "assistant")
    )
    assert "title" in assistant
    assert "kind" not in assistant


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
