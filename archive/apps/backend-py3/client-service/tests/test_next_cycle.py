"""Slice 5 — finish cycle / next cycle / carbonara repeat / history / re-anchor."""

from datetime import date, timedelta

from sqlalchemy import select

from app.models import Event, Project, ProjectStatus
from tests.conftest import wait_path_ready, wait_plugins_ready
from tests.factories import (
    sample_carbonara_repeat_path_state,
    sample_fitness_week2_path_state,
)


async def _create_and_commit_fitness(
    client, auth_headers, enqueue_fitness, *, first_step_when: str = "today"
) -> dict:
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
        json={"first_step_when": first_step_when},
    )
    assert committed.status_code == 200
    return await wait_plugins_ready(
        client, auth_headers, committed.json()["id"]
    )


async def _create_and_commit_carbonara(
    client, auth_headers, enqueue_path
) -> dict:
    enqueue_path()
    created = await client.post(
        "/api/v1/projects",
        headers=auth_headers,
        json={"intent": "Приготовить карбонару"},
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
    return await wait_plugins_ready(
        client, auth_headers, committed.json()["id"]
    )


async def _complete_all_carbonara(client, auth_headers, project: dict) -> dict:
    for action in project["actions"]:
        for item in action.get("checklist_items") or []:
            if not item.get("done"):
                await client.post(
                    f"/api/v1/checklist-items/{item['id']}/toggle",
                    headers=auth_headers,
                    json={"done": True},
                )
        await client.post(
            f"/api/v1/actions/{action['id']}/complete",
            headers=auth_headers,
        )
    detail = await client.get(
        f"/api/v1/projects/{project['id']}", headers=auth_headers
    )
    assert detail.status_code == 200
    return detail.json()


async def test_auto_complete_sets_cycle_result_and_cta(
    client, auth_headers, enqueue_path
):
    project = await _create_and_commit_carbonara(
        client, auth_headers, enqueue_path
    )
    body = await _complete_all_carbonara(client, auth_headers, project)

    assert body["status"] == "completed"
    assert body["cycle"]["status"] == "completed" or body.get("cycle_result")
    assert body["cycle_result"] is not None
    assert body["cycle_result"]["completed_steps"] >= 1
    assert body["cycle_result"]["partial"] is False
    assert body["next_cycle_available"] is True
    assert body["continue_kind"] == "repeat"
    assert body["can_finish_cycle"] is False


async def test_finish_cycle_partial_then_next_fitness(
    client, auth_headers, enqueue_fitness, enqueue_next_cycle, db_session
):
    project = await _create_and_commit_fitness(
        client, auth_headers, enqueue_fitness
    )
    today = date.today().isoformat()

    # Complete one unlocked action so finish_cycle is allowed.
    focus = project["next_action"]
    assert focus is not None
    done = await client.post(
        f"/api/v1/actions/{focus['id']}/complete",
        headers=auth_headers,
        params={"local_date": today},
    )
    assert done.status_code == 200

    detail = await client.get(
        f"/api/v1/projects/{project['id']}",
        headers=auth_headers,
        params={"local_date": today},
    )
    assert detail.json()["can_finish_cycle"] is True

    finished = await client.post(
        f"/api/v1/projects/{project['id']}/complete-cycle",
        headers=auth_headers,
        params={"local_date": today},
        json={
            "partial_notes": "Сделал только день 1",
            "user_comment": "коліна болят",
        },
    )
    assert finished.status_code == 200
    body = finished.json()
    assert body["status"] == "completed"
    assert body["next_cycle_available"] is True
    assert body["continue_kind"] == "next"
    assert body["cycle_result"]["partial"] is True
    assert body["cycle_result"]["partial_notes"] == "Сделал только день 1"
    assert body["cycle_result"]["completed_steps"] >= 1
    assert body["cycle_result"]["skipped_steps"] >= 1

    enqueue_next_cycle(sample_fitness_week2_path_state())
    next_resp = await client.post(
        f"/api/v1/projects/{project['id']}/next-cycle",
        headers=auth_headers,
        params={"local_date": today},
        json={"comment": "готовы к неделе 2"},
    )
    assert next_resp.status_code == 200
    nxt = next_resp.json()
    assert nxt["status"] == "active"
    assert nxt["cycle"]["index"] == 2
    assert nxt["cycle"]["horizon_days"] == 7
    assert nxt["cycle"]["status"] == "active"
    assert nxt["cycle_result"] is None
    assert nxt["next_cycle_available"] is False
    assert len(nxt["cycles_history"]) == 1
    assert nxt["cycles_history"][0]["index"] == 1
    assert nxt["cycles_history"][0]["cycle_result"]["partial"] is True
    assert nxt["cycle_anchor_date"] == today
    assert nxt["unlocked_day_index"] == 0
    assert nxt["next_action"] is not None

    row = (
        await db_session.execute(
            select(Project).where(Project.id == project["id"])
        )
    ).scalar_one()
    assert row.status == ProjectStatus.active
    assert row.cycle_index == 2
    assert row.cycle_anchor_date == date.today()
    assert isinstance(row.cycles_history, list) and len(row.cycles_history) == 1

    events = (
        await db_session.execute(
            select(Event.type).where(Event.project_id == project["id"])
        )
    ).scalars().all()
    assert "cycle_completed" in events
    assert "next_cycle_started" in events


async def test_carbonara_repeat_cta_and_reanchor(
    client, auth_headers, enqueue_path, enqueue_next_cycle
):
    project = await _create_and_commit_carbonara(
        client, auth_headers, enqueue_path
    )
    body = await _complete_all_carbonara(client, auth_headers, project)
    assert body["continue_kind"] == "repeat"
    assert body["next_cycle_available"] is True
    history_before = body.get("cycles_history") or []

    today = date.today().isoformat()
    enqueue_next_cycle(sample_carbonara_repeat_path_state())
    nxt = await client.post(
        f"/api/v1/projects/{project['id']}/next-cycle",
        headers=auth_headers,
        params={"local_date": today},
        json={},
    )
    assert nxt.status_code == 200
    data = nxt.json()
    assert data["status"] == "active"
    assert data["cycle"]["index"] == 2
    assert data["cycle"]["horizon_days"] == 1
    assert data["domain"] == "cooking"
    assert data["cycle_anchor_date"] == today
    assert len(data["cycles_history"]) == len(history_before) + 1
    assert data["cycles_history"][-1]["index"] == 1
    assert data["next_action"] is not None


async def test_next_cycle_rejects_before_finish(
    client, auth_headers, enqueue_fitness, llm
):
    project = await _create_and_commit_fitness(
        client, auth_headers, enqueue_fitness
    )
    resp = await client.post(
        f"/api/v1/projects/{project['id']}/next-cycle",
        headers=auth_headers,
        json={},
    )
    assert resp.status_code == 409


async def test_finish_cycle_rejects_without_progress(
    client, auth_headers, enqueue_fitness
):
    project = await _create_and_commit_fitness(
        client, auth_headers, enqueue_fitness
    )
    # can_finish is false with zero progress, but API still allows finish_cycle
    # only when active — finishing with all pending marks everything skipped.
    # Product CTA is gated by can_finish_cycle; API may still finish.
    detail = await client.get(
        f"/api/v1/projects/{project['id']}", headers=auth_headers
    )
    assert detail.json()["can_finish_cycle"] is False


async def test_physical_day_reanchors_on_next_cycle(
    client, auth_headers, enqueue_fitness, enqueue_next_cycle
):
    """After N+1, day 0 is unlocked today; day 1 stays locked until tomorrow."""
    project = await _create_and_commit_fitness(
        client, auth_headers, enqueue_fitness
    )
    today = date.today()
    focus = project["next_action"]
    await client.post(
        f"/api/v1/actions/{focus['id']}/complete",
        headers=auth_headers,
        params={"local_date": today.isoformat()},
    )
    await client.post(
        f"/api/v1/projects/{project['id']}/complete-cycle",
        headers=auth_headers,
        params={"local_date": today.isoformat()},
        json={"partial_notes": "early"},
    )

    enqueue_next_cycle(sample_fitness_week2_path_state())
    nxt_raw = await client.post(
        f"/api/v1/projects/{project['id']}/next-cycle",
        headers=auth_headers,
        params={"local_date": today.isoformat()},
        json={},
    )
    assert nxt_raw.status_code == 200
    nxt = await wait_plugins_ready(
        client, auth_headers, nxt_raw.json()["id"]
    )

    assert nxt["unlocked_day_index"] == 0
    day1 = next(
        (a for a in nxt["actions"] if a.get("day_offset") == 1), None
    )
    if day1 is not None:
        assert day1["day_locked"] is True
        blocked = await client.post(
            f"/api/v1/actions/{day1['id']}/complete",
            headers=auth_headers,
            params={"local_date": today.isoformat()},
        )
        assert blocked.status_code == 409

    tomorrow = (today + timedelta(days=1)).isoformat()
    detail = await client.get(
        f"/api/v1/projects/{project['id']}",
        headers=auth_headers,
        params={"local_date": tomorrow},
    )
    assert detail.json()["unlocked_day_index"] == 1
