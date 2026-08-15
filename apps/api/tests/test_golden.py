"""Golden utterances → expected ops. LLM is mocked; validator and pain policy are real."""

from __future__ import annotations

from facio_api.main import app, get_llm
from facio_api.patches import (
    AddCuePatch,
    LlmPatchWire,
    LlmTurnWire,
    PatchRejected,
    SetCadencePatch,
    SetTargetPatch,
    TurnOut,
    parse_patch,
    wire_to_turn,
)
from facio_api.policy import apply_pain_policy
from facio_domain.models import CueKind, CueSurface, Subject

from tests.conftest import ScriptedLlm, override_llm


def _ops(payload: dict) -> list[str]:
    return [item["op"] for item in payload.get("patches", [])]


def test_lower_back_adds_do_time_cue_not_target_raise(
    client, turn_body: dict, push_ups: Subject
) -> None:
    llm = ScriptedLlm(
        TurnOut(
            confirmation="держи корпус и ягодицы",
            patches=[
                AddCuePatch(
                    kind=CueKind.correction,
                    text="brace the core and the glutes",
                    surface=CueSurface.do_time,
                ),
                SetTargetPatch(goal=40),
            ],
        )
    )
    override_llm(llm)
    turn_body["utterance"] = "поясница забирает нагрузку"
    response = client.post("/v1/turns", json=turn_body)
    assert response.status_code == 200
    body = response.json()
    assert _ops(body) == ["add_cue"]
    patch = body["patches"][0]
    assert patch["kind"] == "correction"
    assert patch["surface"] == "do-time"
    assert "core" in patch["text"] or "корпус" in patch["text"] or "ягодиц" in patch["text"]
    assert not any(item.get("op") == "set_target" for item in body["patches"])
    kept = apply_pain_policy(turn_body["utterance"], push_ups, llm.result.patches)
    assert [item.op for item in kept] == ["add_cue"]


def test_target_thirty_without_pain(client, turn_body: dict) -> None:
    override_llm(ScriptedLlm(TurnOut(confirmation="цель 30", patches=[SetTargetPatch(goal=30)])))
    turn_body["utterance"] = "цель 30"
    response = client.post("/v1/turns", json=turn_body)
    assert response.status_code == 200
    patch = response.json()["patches"][0]
    assert patch == {"op": "set_target", "current": None, "goal": 30}


def test_three_times_a_week(client, turn_body: dict) -> None:
    override_llm(
        ScriptedLlm(
            TurnOut(
                confirmation="три раза в неделю",
                patches=[SetCadencePatch(count=3, period="week")],
            )
        )
    )
    turn_body["utterance"] = "давай три раза в неделю"
    response = client.post("/v1/turns", json=turn_body)
    assert response.status_code == 200
    patch = response.json()["patches"][0]
    assert patch == {"op": "set_cadence", "count": 3, "period": "week"}


def test_pain_plus_higher_target_is_rejected(client, turn_body: dict) -> None:
    override_llm(ScriptedLlm(TurnOut(confirmation="цель 40", patches=[SetTargetPatch(goal=40)])))
    turn_body["utterance"] = "больно, давай 40"
    response = client.post("/v1/turns", json=turn_body)
    assert response.status_code == 422
    assert "pain" in response.json()["detail"]


def test_add_cue_without_surface_is_422(client, turn_body: dict) -> None:
    class MissingSurfaceLlm:
        async def generate(self, **kwargs):
            return wire_to_turn(
                LlmTurnWire(
                    confirmation="hint",
                    patches=[
                        LlmPatchWire(op="add_cue", kind="correction", text="hold the brace", surface="")
                    ],
                )
            )

    override_llm(MissingSurfaceLlm())
    turn_body["utterance"] = "держи корпус"
    response = client.post("/v1/turns", json=turn_body)
    assert response.status_code == 422
    assert "surface" in response.json()["detail"]

    try:
        parse_patch({"op": "add_cue", "kind": "correction", "text": "hold the brace"})
    except PatchRejected as exc:
        assert "surface" in str(exc).lower()
    else:
        raise AssertionError("add_cue without surface must be rejected")


def test_no_api_key_is_501(client, turn_body: dict) -> None:
    app.dependency_overrides.pop(get_llm, None)
    turn_body["utterance"] = "цель 30"
    response = client.post("/v1/turns", json=turn_body)
    assert response.status_code == 501
    assert "ANTHROPIC_API_KEY" in response.json()["detail"]
