"""Action execution: Сегодня / Сделано / Пропустить / checklist / next-action."""

from sqlalchemy import select

from app.models import Event, Project, ProjectStatus


async def _create_and_commit(client, auth_headers, enqueue_path) -> dict:
    enqueue_path()
    created = await client.post(
        "/api/v1/projects",
        headers=auth_headers,
        json={"intent": "Приготовить карбонару"},
    )
    project = created.json()["project"]
    committed = await client.post(
        f"/api/v1/projects/{project['id']}/commit",
        headers=auth_headers,
        json={"first_step_when": "today"},
    )
    assert committed.status_code == 200
    return committed.json()


async def test_next_action_returns_first_pending(
    client, auth_headers, enqueue_path
):
    project = await _create_and_commit(client, auth_headers, enqueue_path)
    response = await client.get(
        f"/api/v1/projects/{project['id']}/next-action",
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["action"] is not None
    assert body["action"]["status"] == "pending"
    assert body["action"]["why"]
    assert body["action"]["key"] == "buy"


async def test_complete_requires_checklist(
    client, auth_headers, enqueue_path
):
    project = await _create_and_commit(client, auth_headers, enqueue_path)
    buy = next(a for a in project["actions"] if a["key"] == "buy")
    response = await client.post(
        f"/api/v1/actions/{buy['id']}/complete",
        headers=auth_headers,
    )
    assert response.status_code == 409
    assert "checklist" in response.json()["detail"].lower()


async def test_toggle_checklist_then_complete(
    client, auth_headers, enqueue_path, db_session
):
    project = await _create_and_commit(client, auth_headers, enqueue_path)
    buy = next(a for a in project["actions"] if a["key"] == "buy")

    for item in buy["checklist_items"]:
        toggled = await client.post(
            f"/api/v1/checklist-items/{item['id']}/toggle",
            headers=auth_headers,
            json={"done": True},
        )
        assert toggled.status_code == 200
        assert toggled.json()["done"] is True

    done = await client.post(
        f"/api/v1/actions/{buy['id']}/complete",
        headers=auth_headers,
    )
    assert done.status_code == 200
    assert done.json()["status"] == "done"

    event_types = set(
        (
            await db_session.execute(
                select(Event.type).where(Event.project_id == project["id"])
            )
        ).scalars().all()
    )
    assert "checklist_item_toggled" in event_types
    assert "action_done" in event_types
    assert "first_completion" in event_types

    next_action = await client.get(
        f"/api/v1/projects/{project['id']}/next-action",
        headers=auth_headers,
    )
    assert next_action.json()["action"]["key"] == "cook"


async def test_skip_action(client, auth_headers, enqueue_path, db_session):
    project = await _create_and_commit(client, auth_headers, enqueue_path)
    buy = next(a for a in project["actions"] if a["key"] == "buy")
    response = await client.post(
        f"/api/v1/actions/{buy['id']}/skip",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "skipped"

    skipped = (
        await db_session.execute(
            select(Event.type).where(
                Event.project_id == project["id"],
                Event.type == "action_skipped",
            )
        )
    ).scalars().all()
    assert len(skipped) == 1


async def test_completing_all_actions_completes_project(
    client, auth_headers, enqueue_path, db_session
):
    project = await _create_and_commit(client, auth_headers, enqueue_path)

    buy = next(a for a in project["actions"] if a["key"] == "buy")
    for item in buy["checklist_items"]:
        await client.post(
            f"/api/v1/checklist-items/{item['id']}/toggle",
            headers=auth_headers,
            json={"done": True},
        )
    await client.post(
        f"/api/v1/actions/{buy['id']}/complete", headers=auth_headers
    )

    cook = next(a for a in project["actions"] if a["key"] == "cook")
    await client.post(
        f"/api/v1/actions/{cook['id']}/complete", headers=auth_headers
    )

    detail = await client.get(
        f"/api/v1/projects/{project['id']}", headers=auth_headers
    )
    assert detail.json()["status"] == "completed"

    row = (
        await db_session.execute(
            select(Project).where(Project.id == project["id"])
        )
    ).scalar_one()
    assert row.status == ProjectStatus.completed

    completed_events = (
        await db_session.execute(
            select(Event.type).where(
                Event.project_id == project["id"],
                Event.type == "project_completed",
            )
        )
    ).scalars().all()
    assert len(completed_events) == 1


async def test_cannot_complete_on_draft(client, auth_headers, enqueue_path):
    enqueue_path()
    created = await client.post(
        "/api/v1/projects",
        headers=auth_headers,
        json={"intent": "Приготовить карбонару"},
    )
    project = created.json()["project"]
    # Draft actions use stable uuid5 ids in the response but are not ORM rows
    # for /actions/{id}/complete — those require committed ORM actions.
    action_id = project["actions"][0]["id"]
    response = await client.post(
        f"/api/v1/actions/{action_id}/complete",
        headers=auth_headers,
    )
    # Stable draft ids are not persisted → 404 Action not found
    assert response.status_code in {404, 409}
