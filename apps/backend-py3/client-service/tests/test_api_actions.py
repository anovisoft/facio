"""Action execution: Сегодня / Сделано / Пропустить / checklist / next_action."""

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


async def test_next_action_on_summary_and_detail(
    client, auth_headers, enqueue_path
):
    project = await _create_and_commit(client, auth_headers, enqueue_path)

    assert project["next_action"] is not None
    assert project["next_action"]["status"] == "pending"
    assert project["next_action"]["why"]
    assert project["next_action"]["key"] == "buy"

    listed = await client.get(
        "/api/v1/projects",
        headers=auth_headers,
        params={"status": "active"},
    )
    assert listed.status_code == 200
    row = next(p for p in listed.json() if p["id"] == project["id"])
    assert row["next_action"]["key"] == "buy"


async def test_draft_next_action_is_null(client, auth_headers, enqueue_path):
    enqueue_path()
    created = await client.post(
        "/api/v1/projects",
        headers=auth_headers,
        json={"intent": "Приготовить карбонару"},
    )
    project = created.json()["project"]
    assert project["next_action"] is None

    listed = await client.get("/api/v1/projects", headers=auth_headers)
    row = next(p for p in listed.json() if p["id"] == project["id"])
    assert row["next_action"] is None


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

    detail = await client.get(
        f"/api/v1/projects/{project['id']}", headers=auth_headers
    )
    assert detail.json()["next_action"]["key"] == "cook"


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
    body = detail.json()
    assert body["status"] == "completed"
    assert body["next_action"] is None

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


async def test_draft_exposes_timers_preview(client, auth_headers, enqueue_path):
    enqueue_path()
    created = await client.post(
        "/api/v1/projects",
        headers=auth_headers,
        json={"intent": "Приготовить карбонару"},
    )
    project = created.json()["project"]
    cook = next(a for a in project["actions"] if a["key"] == "cook")
    assert len(cook["timers"]) >= 2
    assert {t["signal"] for t in cook["timers"]} >= {"alert", "nudge"}
    assert all(t["completed"] is False for t in cook["timers"])


async def test_counter_update_and_timer_complete(
    client, auth_headers, enqueue_fitness, db_session
):
    enqueue_fitness()
    created = await client.post(
        "/api/v1/projects",
        headers=auth_headers,
        json={"intent": "Хочу научиться делать 30 отжиманий"},
    )
    project = created.json()["project"]
    committed = await client.post(
        f"/api/v1/projects/{project['id']}/commit",
        headers=auth_headers,
        json={"first_step_when": "today"},
    )
    assert committed.status_code == 200
    project = committed.json()
    train = next(a for a in project["actions"] if a["key"] == "d0")
    assert train["counter"] is not None
    assert train["counter"]["current"] == 0

    bumped = await client.post(
        f"/api/v1/actions/{train['id']}/counter",
        headers=auth_headers,
        json={"delta": 5},
    )
    assert bumped.status_code == 200
    assert bumped.json()["counter"]["current"] == 5

    set_abs = await client.post(
        f"/api/v1/actions/{train['id']}/counter",
        headers=auth_headers,
        json={"current": 10},
    )
    assert set_abs.status_code == 200
    assert set_abs.json()["counter"]["current"] == 10

    events = set(
        (
            await db_session.execute(
                select(Event.type).where(Event.project_id == project["id"])
            )
        ).scalars().all()
    )
    assert "counter_updated" in events


async def test_timer_complete_on_cook_step(
    client, auth_headers, enqueue_path, db_session
):
    project = await _create_and_commit(client, auth_headers, enqueue_path)
    # Skip buy to reach cook
    buy = next(a for a in project["actions"] if a["key"] == "buy")
    await client.post(
        f"/api/v1/actions/{buy['id']}/skip", headers=auth_headers
    )
    detail = await client.get(
        f"/api/v1/projects/{project['id']}", headers=auth_headers
    )
    cook = detail.json()["next_action"]
    assert cook["key"] == "cook"
    assert cook["timers"]
    timer_id = cook["timers"][0]["id"]

    done = await client.post(
        f"/api/v1/actions/{cook['id']}/timers/{timer_id}/complete",
        headers=auth_headers,
        json={"completed": True},
    )
    assert done.status_code == 200
    matched = next(t for t in done.json()["timers"] if t["id"] == timer_id)
    assert matched["completed"] is True

    events = (
        await db_session.execute(
            select(Event.type).where(
                Event.project_id == project["id"],
                Event.type == "timer_completed",
            )
        )
    ).scalars().all()
    assert len(events) == 1
