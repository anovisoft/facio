"""Create intent gate: path | instant_answer + progressive start surface."""

from sqlalchemy import select

from app.models import Event, LlmCall, Project, StateVersion
from app.schemas.path_state import PATH_RESPONSE_SCHEMA
from app.schemas.create_response import CREATE_GATE_SCHEMA
from tests.conftest import wait_path_ready
from tests.factories import sample_create_path, sample_instant_answer


_GATE_PATH = {
    "kind": "path",
    "instant_answer": {
        "label": "",
        "answer": "",
        "goal_suggestions": [],
        "domain": "other",
    },
    "path_start": {
        "paraphrase": "Ок — ведём к: карбонара",
        "title": "Карбонара на ужин",
        "summary": "За вечер купим продукты и приготовим карбонару.",
        "questions": [
            {
                "id": "meat",
                "prompt": "Какое мясо возьмёте?",
                "options": ["гуанчиале", "панчетта"],
            },
            {
                "id": "servings",
                "prompt": "На сколько порций?",
                "options": ["1", "2"],
            },
        ],
        "outline_days": ["Вечер готовки"],
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
    assert project["paraphrase"]
    assert project["title"]
    assert project["summary"]
    assert project["path_ready"] is False
    assert project["current_version"] == 1
    assert len(project["actions"]) == 0
    assert len(project["questions"]) == 2

    project_id = project["id"]
    ready = await wait_path_ready(client, auth_headers, project_id)
    assert ready["path_ready"] is True
    assert ready["outcome"]
    assert ready["domain"] == "cooking"
    assert len(ready["actions"]) >= 1
    assert all(a["why"] for a in ready["actions"])
    assert ready["current_version"] == 2
    cook = next(a for a in ready["actions"] if a["key"] == "cook")
    assert "timeline" in cook["plugin_hints"]
    assert cook.get("timeline") is None
    assert ready.get("plugins_ready") is False

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
    assert len(versions) == 2
    assert all(v.source.value == "llm_create" for v in versions)

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
            "path_start": {
                "paraphrase": "",
                "title": "",
                "summary": "",
                "questions": [],
                "outline_days": [],
            },
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
    project_id = response.json()["project"]["id"]
    ready = await wait_path_ready(client, auth_headers, project_id)
    assert ready["path_ready"] is True
    # gate + invalid path + retry path
    assert len(llm.calls) == 3


async def test_create_retry_message_asks_to_shrink_horizon_too(
    client, auth_headers, llm
):
    """fit_sample hotfix: the retry nudge for an over-long actions[] must
    also tell the model to shrink cycle.horizon_days / days[] — not trim
    actions alone into a still-hollow multi-week shell.

    Use >16 actions all inside the fitness week (day_offset < 7) so the
    horizon truncate cannot silently drop them under the actions cap.
    """
    from tests.factories import sample_fitness_path_state

    base = sample_fitness_path_state()
    seed = base["actions"][0]
    too_many = [
        dict(seed, id=f"overflow{i}", day_offset=i % 7, sort=i)
        for i in range(17)
    ]
    too_long = dict(base, actions=too_many)
    assert len(too_long["actions"]) > 16

    llm.enqueue("create", _GATE_PATH)
    llm.enqueue("create", too_long)
    llm.enqueue("create", sample_create_path()["path"])

    response = await client.post(
        "/api/v1/projects",
        headers=auth_headers,
        json={"intent": "Хочу научиться делать 30 отжиманий"},
    )
    assert response.status_code == 200
    project_id = response.json()["project"]["id"]
    ready = await wait_path_ready(client, auth_headers, project_id)
    assert ready["path_ready"] is True

    # gate + invalid (too many actions) + retry path
    assert len(llm.calls) == 3
    retry_message = llm.calls[2]["messages"][-1]["content"]
    assert "horizon_days" in retry_message
    assert "actions" in retry_message
    assert "pad" in retry_message.lower() or "hollow" in retry_message.lower()


async def test_create_fails_after_two_invalid(client, auth_headers, llm, db_session):
    import asyncio

    from sqlalchemy import select

    from app.models import LlmCall

    bad = {"outcome": "incomplete"}
    llm.enqueue("create", _GATE_PATH)
    llm.enqueue("create", bad)
    llm.enqueue("create", bad)
    response = await client.post(
        "/api/v1/projects",
        headers=auth_headers,
        json={"intent": "Приготовить карбонару"},
    )
    # Phase-1 succeeds; phase-2 fails in background — create still 200.
    assert response.status_code == 200
    project = response.json()["project"]
    assert project["path_ready"] is False
    # Background exhausted retries; path stays not ready + surfaces error.
    await asyncio.sleep(0.3)
    detail = await client.get(
        f"/api/v1/projects/{project['id']}", headers=auth_headers
    )
    assert detail.status_code == 200
    body = detail.json()
    assert body["path_ready"] is False
    assert body.get("path_error")
    assert len(llm.calls) == 3
    # Failed path llm_calls must remain in audit (not rolled back).
    llm_rows = (
        await db_session.execute(
            select(LlmCall).where(LlmCall.project_id == project["id"])
        )
    ).scalars().all()
    assert len(llm_rows) >= 2
    assert any(not c.parsed_ok for c in llm_rows)
