from httpx import ASGITransport, AsyncClient

from facio_domain.desk import founding_desk

from facio_api.config import Settings, get_settings
from facio_api.main import app
from facio_api.talk.schemas import TalkSelection, TalkTurnRequest


async def test_health(client) -> None:
    response = await client.get("/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["mode"] == "scripted"
    assert body["provider"] == "openai"
    assert body["model"] == "gpt-4o-mini"


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


async def test_live_haiku_without_anthropic_key_is_503() -> None:
    settings = Settings(
        talk_mode="live",
        model_name="haiku",
        openai_api_key="sk-openai",
        anthropic_api_key=None,
    )
    app.dependency_overrides[get_settings] = lambda: settings
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as session:
            body = TalkTurnRequest(utterance="hi", desk=founding_desk())
            response = await session.post("/v1/talk/turn", json=body.model_dump(mode="json"))
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 503
    assert "anthropic" in response.json()["detail"]


async def test_locale_defaults_to_ru_for_old_clients(client) -> None:
    """`locale` is optional on the wire; the response schema does not grow."""
    payload = {
        "utterance": "поясница забирает нагрузку",
        "desk": founding_desk().model_dump(mode="json"),
        "thread_id": "t-locale-default",
    }
    assert "locale" not in payload
    response = await client.post("/v1/talk/turn", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["mutated"] is True
    assert "locale" not in body


async def test_locale_en_turn_matches_the_english_golden(client) -> None:
    body = TalkTurnRequest(
        utterance="my lower back takes the load",
        desk=founding_desk(),
        thread_id="t-locale-en",
        locale="en",
    )
    response = await client.post("/v1/talk/turn", json=body.model_dump(mode="json"))
    assert response.status_code == 200
    payload = response.json()
    assert payload["mutated"] is True
    assert any(cue["id"] == "push-ups-brace-en-talk" for cue in payload["desk"]["cues"])


async def test_unknown_locale_rejected(client) -> None:
    body = {
        "utterance": "поясница забирает нагрузку",
        "desk": founding_desk().model_dump(mode="json"),
        "locale": "de",
    }
    response = await client.post("/v1/talk/turn", json=body)
    assert response.status_code == 422


async def test_selection_turn_lands_a_clarification_behind_a_question_mark(client) -> None:
    """R3: the phrase the person picked comes back as an on-demand cue with its quote."""
    body = TalkTurnRequest(
        utterance="что это значит: не роняй таз?",
        desk=founding_desk(),
        thread_id="t-selection",
        selection=TalkSelection(
            quote="не роняй таз",
            widget_id="push-ups-counter",
            step_id="rep-1",
        ),
    )
    response = await client.post("/v1/talk/turn", json=body.model_dump(mode="json"))
    assert response.status_code == 200
    payload = response.json()
    assert payload["mutated"] is True
    cue = next(row for row in payload["desk"]["cues"] if row["id"] == "push-ups-hips-talk")
    assert cue["kind"] == "clarification"
    assert cue["surface"] == "on-demand"
    assert cue["step_id"] == "rep-1"
    assert cue["quote"] == "не роняй таз"


async def test_selection_with_no_binding_leaves_the_desk_alone(client) -> None:
    """A selection with no bound subject produces no cue ([05])."""
    body = TalkTurnRequest(
        utterance="что это значит: беговая экономичность?",
        desk=founding_desk(),
        thread_id="t-orphan",
        selection=TalkSelection(quote="беговая экономичность"),
    )
    response = await client.post("/v1/talk/turn", json=body.model_dump(mode="json"))
    assert response.status_code == 200
    payload = response.json()
    assert payload["mutated"] is False
    assert payload["tool_calls"] == []
    assert payload["snapshots"] == []
    assert len(payload["desk"]["cues"]) == len(founding_desk().cues)
    assert payload["text"]


async def test_selection_is_optional_on_the_wire(client) -> None:
    """Old clients send no `selection`; the turn is unchanged."""
    body = {
        "utterance": "поясница забирает нагрузку",
        "desk": founding_desk().model_dump(mode="json"),
        "thread_id": "t-old",
    }
    response = await client.post("/v1/talk/turn", json=body)
    assert response.status_code == 200
    assert response.json()["mutated"] is True
