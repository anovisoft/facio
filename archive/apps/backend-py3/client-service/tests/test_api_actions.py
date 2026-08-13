"""Action execution: Сегодня / Сделано / Пропустить / checklist / next_action."""

from sqlalchemy import select

from app.models import Event, Project, ProjectStatus
from tests.conftest import wait_path_ready, wait_plugins_ready


async def _create_and_commit(client, auth_headers, enqueue_path) -> dict:
    enqueue_path()
    created = await client.post(
        "/api/v1/projects",
        headers=auth_headers,
        json={"intent": "Приготовить карбонару"},
    )
    project = created.json()["project"]
    await wait_path_ready(client, auth_headers, project["id"])
    committed = await client.post(
        f"/api/v1/projects/{project['id']}/commit",
        headers=auth_headers,
        json={"first_step_when": "today"},
    )
    assert committed.status_code == 200
    return await wait_plugins_ready(
        client, auth_headers, committed.json()["id"]
    )


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
    project = await wait_path_ready(
        client, auth_headers, created.json()["project"]["id"]
    )
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
    assert detail.json()["next_action"]["key"] == "prep"


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


async def test_uncomplete_done_and_skipped(
    client, auth_headers, enqueue_path, db_session
):
    """Session Back: done/skipped → pending; checklist runtime kept."""
    project = await _create_and_commit(client, auth_headers, enqueue_path)
    buy = next(a for a in project["actions"] if a["key"] == "buy")

    for item in buy["checklist_items"]:
        await client.post(
            f"/api/v1/checklist-items/{item['id']}/toggle",
            headers=auth_headers,
            json={"done": True},
        )
    done = await client.post(
        f"/api/v1/actions/{buy['id']}/complete",
        headers=auth_headers,
    )
    assert done.status_code == 200
    assert done.json()["status"] == "done"
    assert all(i["done"] for i in done.json()["checklist_items"])

    reopened = await client.post(
        f"/api/v1/actions/{buy['id']}/uncomplete",
        headers=auth_headers,
    )
    assert reopened.status_code == 200
    body = reopened.json()
    assert body["status"] == "pending"
    assert all(i["done"] for i in body["checklist_items"])

    events = set(
        (
            await db_session.execute(
                select(Event.type).where(Event.project_id == project["id"])
            )
        ).scalars().all()
    )
    assert "action_uncompleted" in events

    # Skip then uncomplete also works.
    skipped = await client.post(
        f"/api/v1/actions/{buy['id']}/skip",
        headers=auth_headers,
    )
    assert skipped.status_code == 200
    again = await client.post(
        f"/api/v1/actions/{buy['id']}/uncomplete",
        headers=auth_headers,
    )
    assert again.status_code == 200
    assert again.json()["status"] == "pending"

    # Pending cannot be uncompleted.
    bad = await client.post(
        f"/api/v1/actions/{buy['id']}/uncomplete",
        headers=auth_headers,
    )
    assert bad.status_code == 409


async def test_uncomplete_rejected_on_locked_day(
    client, auth_headers, enqueue_fitness
):
    """Physical-day gate: cannot uncomplete a future day's action."""
    from datetime import date, timedelta

    from tests.conftest import wait_path_ready, wait_plugins_ready

    enqueue_fitness()
    created = await client.post(
        "/api/v1/projects",
        headers=auth_headers,
        json={"intent": "Хочу научиться делать 30 отжиманий"},
    )
    project = await wait_path_ready(
        client, auth_headers, created.json()["project"]["id"]
    )
    committed = await client.post(
        f"/api/v1/projects/{project['id']}/commit",
        headers=auth_headers,
        json={"first_step_when": "today"},
    )
    assert committed.status_code == 200
    project = await wait_plugins_ready(
        client, auth_headers, committed.json()["id"]
    )
    d0 = next(a for a in project["actions"] if a["day_offset"] == 0)
    future = next(a for a in project["actions"] if a["day_offset"] == 1)
    assert (
        await client.post(
            f"/api/v1/actions/{d0['id']}/skip", headers=auth_headers
        )
    ).status_code == 200
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    assert (
        await client.post(
            f"/api/v1/actions/{future['id']}/skip",
            headers=auth_headers,
            params={"local_date": tomorrow},
        )
    ).status_code == 200
    locked = await client.post(
        f"/api/v1/actions/{future['id']}/uncomplete",
        headers=auth_headers,
        params={"local_date": date.today().isoformat()},
    )
    assert locked.status_code == 409
    assert "open yet" in locked.json()["detail"].lower()


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
    assert (
        await client.post(
            f"/api/v1/actions/{buy['id']}/complete", headers=auth_headers
        )
    ).status_code == 200

    prep = next(a for a in project["actions"] if a["key"] == "prep")
    for item in prep["checklist_items"]:
        await client.post(
            f"/api/v1/checklist-items/{item['id']}/toggle",
            headers=auth_headers,
            json={"done": True},
        )
    assert (
        await client.post(
            f"/api/v1/actions/{prep['id']}/complete", headers=auth_headers
        )
    ).status_code == 200

    cook = next(a for a in project["actions"] if a["key"] == "cook")
    assert (
        await client.post(
            f"/api/v1/actions/{cook['id']}/complete", headers=auth_headers
        )
    ).status_code == 200

    detail = await client.get(
        f"/api/v1/projects/{project['id']}", headers=auth_headers
    )
    body = detail.json()
    assert body["status"] == "completed"
    assert body["next_action"] is None
    assert body["cycle_result"] is not None
    assert body["next_cycle_available"] is True
    assert body["continue_kind"] == "repeat"

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
    project = await wait_path_ready(
        client, auth_headers, created.json()["project"]["id"]
    )
    # Draft actions use stable uuid5 ids in the response but are not ORM rows
    # for /actions/{id}/complete — those require committed ORM actions.
    action_id = project["actions"][0]["id"]
    response = await client.post(
        f"/api/v1/actions/{action_id}/complete",
        headers=auth_headers,
    )
    # Stable draft ids are not persisted → 404 Action not found
    assert response.status_code in {404, 409}


async def test_draft_exposes_plugin_hints(client, auth_headers, enqueue_path):
    enqueue_path()
    created = await client.post(
        "/api/v1/projects",
        headers=auth_headers,
        json={"intent": "Приготовить карбонару"},
    )
    project = await wait_path_ready(
        client, auth_headers, created.json()["project"]["id"]
    )
    cook = next(a for a in project["actions"] if a["key"] == "cook")
    assert "timeline" in cook["plugin_hints"]
    # Full payloads arrive after Start (#3), not on draft Path wire.
    assert cook.get("timeline") is None
    assert cook.get("timers") == []


async def test_stepper_materialize_and_beat_counter(
    client, auth_headers, enqueue_fitness, db_session
):
    enqueue_fitness()
    created = await client.post(
        "/api/v1/projects",
        headers=auth_headers,
        json={"intent": "Хочу научиться делать 30 отжиманий"},
    )
    project = await wait_path_ready(
        client, auth_headers, created.json()["project"]["id"]
    )
    d0 = next(a for a in project["actions"] if a["key"] == "d0")
    assert d0["plugin_hints"] == ["stepper"]
    committed = await client.post(
        f"/api/v1/projects/{project['id']}/commit",
        headers=auth_headers,
        json={"first_step_when": "today"},
    )
    assert committed.status_code == 200
    project = await wait_plugins_ready(
        client, auth_headers, committed.json()["id"]
    )
    train = next(a for a in project["actions"] if a["key"] == "d0")
    assert train["counter"] is None
    assert train["interval_plan"] is None
    assert train["stepper"] is not None
    beats = train["stepper"]["beats"]
    assert len(beats) >= 3
    assert beats[0]["kind"] == "measure"
    assert beats[0]["counter"] is not None
    measure_id = beats[0]["id"]

    bumped = await client.post(
        f"/api/v1/actions/{train['id']}/stepper/beats/{measure_id}/counter",
        headers=auth_headers,
        json={"delta": 5},
    )
    assert bumped.status_code == 200
    bumped_beats = bumped.json()["stepper"]["beats"]
    measure = next(b for b in bumped_beats if b["id"] == measure_id)
    assert measure["counter"]["current"] == 5

    set_abs = await client.post(
        f"/api/v1/actions/{train['id']}/stepper/beats/{measure_id}/counter",
        headers=auth_headers,
        json={"current": 10},
    )
    assert set_abs.status_code == 200
    set_beats = set_abs.json()["stepper"]["beats"]
    measure = next(b for b in set_beats if b["id"] == measure_id)
    assert measure["counter"]["current"] == 10

    events = set(
        (
            await db_session.execute(
                select(Event.type).where(Event.project_id == project["id"])
            )
        ).scalars().all()
    )
    assert "counter_updated" in events


async def test_timer_complete_on_isolated_timers_step(
    client, auth_headers, enqueue_path, db_session
):
    """Timers API: isolated timers action (XOR with cook timeline)."""
    from tests.factories import (
        sample_path_state,
        sample_plugins_materialize_with_isolated_timer,
    )

    path = sample_path_state()
    # Replace prep checklist with an isolated timers wait (dough-style).
    path["actions"][1] = {
        "id": "proof",
        "title": "Расстойка теста",
        "why": "Изолированное ожидание без оси сессии",
        "detail": "Ручной Start",
        "estimate_min": 10,
        "day_offset": 0,
        "sort": 1,
        "group_id": "prep",
        "checklist_items": [],
        "plugin_hints": ["timers"],
        "timers": [],
        "counter": None,
        "timeline": None,
        "interval_plan": None,
        "stepper": None,
    }
    enqueue_path(
        path_overrides={"actions": path["actions"]},
        plugins=sample_plugins_materialize_with_isolated_timer(),
    )
    created = await client.post(
        "/api/v1/projects",
        headers=auth_headers,
        json={"intent": "Приготовить карбонару"},
    )
    project = created.json()["project"]
    await wait_path_ready(client, auth_headers, project["id"])
    committed = await client.post(
        f"/api/v1/projects/{project['id']}/commit",
        headers=auth_headers,
        json={"first_step_when": "today"},
    )
    assert committed.status_code == 200
    project = await wait_plugins_ready(
        client, auth_headers, committed.json()["id"]
    )

    buy = next(a for a in project["actions"] if a["key"] == "buy")
    await client.post(
        f"/api/v1/actions/{buy['id']}/skip", headers=auth_headers
    )
    detail = await client.get(
        f"/api/v1/projects/{project['id']}", headers=auth_headers
    )
    proof = detail.json()["next_action"]
    assert proof["key"] == "proof"
    assert proof["timers"]
    timer_id = proof["timers"][0]["id"]

    done = await client.post(
        f"/api/v1/actions/{proof['id']}/timers/{timer_id}/complete",
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
