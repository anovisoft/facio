from facio_domain.desk import founding_desk

from facio_api.schemas import TalkTurnRequest


async def test_health(client) -> None:
    response = await client.get("/v1/health")
    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert response.json()["mode"] == "scripted"


async def test_lower_back_turn(client) -> None:
    body = TalkTurnRequest(
        utterance="поясница забирает нагрузку",
        desk=founding_desk(),
        thread_id="t1",
    )
    response = await client.post("/v1/talk/turn", json=body.model_dump(mode="json"))
    assert response.status_code == 200
    payload = response.json()
    assert payload["mutated"] is True
    assert payload["snapshots"]
    assert any(cue["id"] == "push-ups-brace-talk" for cue in payload["desk"]["cues"])


async def test_empty_utterance_rejected(client) -> None:
    body = TalkTurnRequest(utterance="   ", desk=founding_desk())
    response = await client.post("/v1/talk/turn", json=body.model_dump(mode="json"))
    assert response.status_code == 422
