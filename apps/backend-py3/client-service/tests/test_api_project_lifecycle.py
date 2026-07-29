"""Project lifecycle: list filters, refine, restore, commit, abandon, multi-active."""

from sqlalchemy import select

from app.models import Event, Project, ProjectStatus, StateVersion
from tests.factories import refined_path_state, sample_path_state


async def _create_draft(client, auth_headers, enqueue_path) -> dict:
    enqueue_path()
    response = await client.post(
        "/api/v1/projects",
        headers=auth_headers,
        json={"intent": "Приготовить карбонару"},
    )
    assert response.status_code == 200
    return response.json()["project"]


async def test_list_status_filters(
    client, auth_headers, enqueue_path, enqueue_refine
):
    draft = await _create_draft(client, auth_headers, enqueue_path)

    open_list = await client.get("/api/v1/projects", headers=auth_headers)
    assert open_list.status_code == 200
    assert len(open_list.json()) == 1

    draft_list = await client.get(
        "/api/v1/projects", headers=auth_headers, params={"status": "draft"}
    )
    assert [p["id"] for p in draft_list.json()] == [draft["id"]]

    # Commit then abandon path covered elsewhere; empty abandoned.
    abandoned = await client.get(
        "/api/v1/projects",
        headers=auth_headers,
        params={"status": "abandoned"},
    )
    assert abandoned.json() == []


async def test_refine_creates_new_state_version(
    client, auth_headers, enqueue_path, enqueue_refine, db_session
):
    project = await _create_draft(client, auth_headers, enqueue_path)
    enqueue_refine()

    response = await client.post(
        f"/api/v1/projects/{project['id']}/refine",
        headers=auth_headers,
        json={"answer": "2", "question_id": "q_servings"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["current_version"] == 2
    assert body["questions"] == []

    events = (
        await db_session.execute(
            select(Event.type).where(
                Event.project_id == project["id"],
                Event.type == "refine_answered",
            )
        )
    ).scalars().all()
    assert len(events) == 1


async def test_restore_state_appends_user_restore(
    client, auth_headers, enqueue_path, enqueue_refine, db_session
):
    project = await _create_draft(client, auth_headers, enqueue_path)
    enqueue_refine()
    await client.post(
        f"/api/v1/projects/{project['id']}/refine",
        headers=auth_headers,
        json={"answer": "2", "question_id": "q_servings"},
    )

    response = await client.post(
        f"/api/v1/projects/{project['id']}/restore-state",
        headers=auth_headers,
        json={"version": 1},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["current_version"] == 3
    assert len(body["questions"]) == 2

    sources = (
        await db_session.execute(
            select(StateVersion.source).where(
                StateVersion.project_id == project["id"]
            )
        )
    ).scalars().all()
    assert [s.value for s in sources] == [
        "llm_create",
        "llm_refine",
        "user_restore",
    ]

    back = (
        await db_session.execute(
            select(Event).where(
                Event.project_id == project["id"],
                Event.type == "back_navigated",
            )
        )
    ).scalar_one()
    assert back.payload["restored_from_version"] == 1


async def test_commit_activates_and_materializes(
    client, auth_headers, enqueue_path, db_session
):
    project = await _create_draft(client, auth_headers, enqueue_path)
    response = await client.post(
        f"/api/v1/projects/{project['id']}/commit",
        headers=auth_headers,
        json={"first_step_when": "today"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "active"
    assert body["committed_at"] is not None
    assert len(body["actions"]) >= 1
    assert all(a["due_at"] is not None for a in body["actions"])
    assert any(a["checklist_items"] for a in body["actions"])

    events = (
        await db_session.execute(
            select(Event.type).where(
                Event.project_id == project["id"], Event.type == "committed"
            )
        )
    ).scalars().all()
    assert len(events) == 1

    # Draft state endpoints now return ORM actions
    actions = await client.get(
        f"/api/v1/projects/{project['id']}/actions", headers=auth_headers
    )
    assert actions.status_code == 200
    assert len(actions.json()) >= 1


async def test_multi_active_projects_allowed(
    client, auth_headers, enqueue_path
):
    first = await _create_draft(client, auth_headers, enqueue_path)
    await client.post(
        f"/api/v1/projects/{first['id']}/commit",
        headers=auth_headers,
        json={},
    )

    enqueue_path()
    second = await _create_draft(client, auth_headers, enqueue_path)
    await client.post(
        f"/api/v1/projects/{second['id']}/commit",
        headers=auth_headers,
        json={},
    )

    active = await client.get(
        "/api/v1/projects",
        headers=auth_headers,
        params={"status": "active"},
    )
    assert len(active.json()) == 2


async def test_abandon_moves_to_archive(
    client, auth_headers, enqueue_path, db_session
):
    project = await _create_draft(client, auth_headers, enqueue_path)
    response = await client.post(
        f"/api/v1/projects/{project['id']}/abandon",
        headers=auth_headers,
        json={"reason": "передумал"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "abandoned"

    open_list = await client.get("/api/v1/projects", headers=auth_headers)
    assert open_list.json() == []

    archived = await client.get(
        "/api/v1/projects",
        headers=auth_headers,
        params={"status": "abandoned"},
    )
    assert len(archived.json()) == 1

    row = (
        await db_session.execute(
            select(Project).where(Project.id == project["id"])
        )
    ).scalar_one()
    assert row.status == ProjectStatus.abandoned


async def test_cannot_commit_twice(client, auth_headers, enqueue_path):
    project = await _create_draft(client, auth_headers, enqueue_path)
    await client.post(
        f"/api/v1/projects/{project['id']}/commit",
        headers=auth_headers,
        json={},
    )
    response = await client.post(
        f"/api/v1/projects/{project['id']}/commit",
        headers=auth_headers,
        json={},
    )
    assert response.status_code == 409


async def test_repair_on_active(
    client, auth_headers, enqueue_path, enqueue_repair
):
    project = await _create_draft(client, auth_headers, enqueue_path)
    await client.post(
        f"/api/v1/projects/{project['id']}/commit",
        headers=auth_headers,
        json={},
    )
    enqueue_repair(sample_path_state(questions=[], paraphrase="Сдвинули план"))
    response = await client.post(
        f"/api/v1/projects/{project['id']}/repair",
        headers=auth_headers,
        json={"reason": "нет гуанчиале, возьму бекон"},
    )
    assert response.status_code == 200
    assert response.json()["current_version"] == 2
    assert "Сдвинули" in response.json()["paraphrase"]


async def test_get_project_not_found(client, auth_headers):
    response = await client.get(
        "/api/v1/projects/00000000-0000-0000-0000-000000000001",
        headers=auth_headers,
    )
    assert response.status_code == 404


async def test_refine_only_on_draft(client, auth_headers, enqueue_path, llm):
    project = await _create_draft(client, auth_headers, enqueue_path)
    await client.post(
        f"/api/v1/projects/{project['id']}/commit",
        headers=auth_headers,
        json={},
    )
    llm.enqueue("refine", refined_path_state())
    response = await client.post(
        f"/api/v1/projects/{project['id']}/refine",
        headers=auth_headers,
        json={"answer": "2"},
    )
    assert response.status_code == 409
