"""Create intent gate: path | instant_answer + audit trail."""

from sqlalchemy import select

from app.models import Event, LlmCall, Project, StateVersion
from app.schemas.path_state import PATH_RESPONSE_SCHEMA
from app.schemas.create_response import CREATE_GATE_SCHEMA
from tests.factories import sample_create_path, sample_instant_answer


_GATE_PATH = {
    "kind": "path",
    "instant_answer": {
        "label": "",
        "answer": "",
        "goal_suggestions": [],
        "domain": "other",
    },
}


async def test_create_path_project(
    client, auth_headers, enqueue_path, db_session, llm
):
    enqueue_path()
    response = await client.post(
        "/api/v1/projects",
        headers=auth_headers,
        json={"intent": "Приготовить карбонару"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["kind"] == "path"
    project = body["project"]
    assert project["status"] == "draft"
    assert project["raw_intent"] == "Приготовить карбонару"
    assert project["outcome"]
    assert project["paraphrase"]
    assert project["title"]
    assert project["summary"]
    assert project["domain"] == "cooking"
    assert project["current_version"] == 1
    assert len(project["actions"]) >= 1
    assert all(a["why"] for a in project["actions"])
    assert len(project["questions"]) == 2

    project_id = project["id"]
    events = (
        await db_session.execute(
            select(Event.type).where(Event.project_id == project_id)
        )
    ).scalars().all()
    assert "intent_submitted" in events
    assert "soft_start_shown" in events
    assert "draft_shown" in events

    versions = (
        await db_session.execute(
            select(StateVersion).where(StateVersion.project_id == project_id)
        )
    ).scalars().all()
    assert len(versions) == 1
    assert versions[0].source.value == "llm_create"

    llm_calls = (
        await db_session.execute(
            select(LlmCall).where(LlmCall.project_id == project_id)
        )
    ).scalars().all()
    # Gate + path generation (both purpose=create, both attached to project).
    assert len(llm_calls) == 2
    assert all(c.parsed_ok is True for c in llm_calls)
    assert all(c.raw_response is not None for c in llm_calls)
    assert len(llm.calls) == 2
    assert llm.calls[0]["purpose"] == "create"
    assert llm.calls[1]["purpose"] == "create"
    assert llm.calls[0]["response_schema"] == CREATE_GATE_SCHEMA
    assert llm.calls[1]["response_schema"] == PATH_RESPONSE_SCHEMA


async def test_create_instant_answer_no_project(
    client, auth_headers, llm, db_session
):
    # Gate-only: instant_answer payload without path branch.
    ia = sample_instant_answer()
    llm.enqueue(
        "create",
        {
            "kind": "instant_answer",
            "instant_answer": ia["instant_answer"],
        },
    )
    response = await client.post(
        "/api/v1/projects",
        headers=auth_headers,
        json={"intent": "Сколько будет 2 в 100 степени?"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["kind"] == "instant_answer"
    assert "2^100" in body["answer"] or "1267650600228229401496703205376" in body["answer"]
    assert len(body["goal_suggestions"]) >= 2
    assert body["llm_call_id"]
    assert body["event_id"]

    projects = (await db_session.execute(select(Project))).scalars().all()
    assert projects == []

    events = (
        await db_session.execute(
            select(Event.type).where(Event.type == "instant_answer_shown")
        )
    ).scalars().all()
    assert len(events) == 1
    assert len(llm.calls) == 1


async def test_create_without_llm_returns_501(client, auth_headers, llm):
    # No enqueue → ScriptedLLM raises; PathService maps NotConfigured when
    # using NotConfiguredLLMProvider. Here empty queue is RuntimeError → 502.
    # Override with NotConfiguredLLMProvider for true 501.
    from app.providers.llm import NotConfiguredLLMProvider, set_llm_provider

    set_llm_provider(NotConfiguredLLMProvider())
    from app.deps import provide_llm
    from app.main import app

    app.dependency_overrides[provide_llm] = lambda: NotConfiguredLLMProvider()

    response = await client.post(
        "/api/v1/projects",
        headers=auth_headers,
        json={"intent": "something"},
    )
    assert response.status_code == 501


async def test_create_retries_invalid_then_succeeds(
    client, auth_headers, llm
):
    llm.enqueue("create", _GATE_PATH)
    llm.enqueue("create", {"outcome": "bad"})
    llm.enqueue("create", sample_create_path()["path"])
    response = await client.post(
        "/api/v1/projects",
        headers=auth_headers,
        json={"intent": "Приготовить карбонару"},
    )
    assert response.status_code == 200
    assert response.json()["kind"] == "path"
    # gate + invalid path + retry path
    assert len(llm.calls) == 3


async def test_create_fails_after_two_invalid(client, auth_headers, llm):
    bad = {"outcome": "incomplete"}
    llm.enqueue("create", _GATE_PATH)
    llm.enqueue("create", bad)
    llm.enqueue("create", bad)
    response = await client.post(
        "/api/v1/projects",
        headers=auth_headers,
        json={"intent": "Приготовить карбонару"},
    )
    assert response.status_code == 422
