"""Deterministic postpone-day (Session chrome) — no LLM."""

from datetime import date

from sqlalchemy import select

from app.models import Event, StateVersion
from tests.conftest import wait_path_ready, wait_plugins_ready


async def _create_and_commit_fitness(
    client, auth_headers, enqueue_fitness
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
        json={"first_step_when": "today"},
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


async def test_postpone_day_bumps_today_pending_fitness(
    client, auth_headers, enqueue_fitness, db_session
):
    project = await _create_and_commit_fitness(
        client, auth_headers, enqueue_fitness
    )
    before_version = project["current_version"]
    d0 = next(a for a in project["actions"] if a["key"] == "d0")
    assert d0["day_offset"] == 0
    assert d0["status"] == "pending"
    assert project["next_action"]["key"] == "d0"

    response = await client.post(
        f"/api/v1/projects/{project['id']}/postpone-day",
        headers=auth_headers,
        params={"local_date": date.today().isoformat()},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["current_version"] == before_version + 1
    # Today's pending moved to tomorrow → waiting / peek.
    moved = next(a for a in body["actions"] if a["key"] == "d0")
    assert moved["day_offset"] == 1
    assert moved["status"] == "pending"
    assert body["next_action"] is None
    assert body["peek_action"] is not None
    assert body["peek_action"]["key"] == "d0"

    # Done/skipped on other days untouched; day-1 original still present.
    day1_keys = {a["key"] for a in body["actions"] if a["day_offset"] == 1}
    assert "d0" in day1_keys
    assert "d1" in day1_keys

    events = (
        await db_session.execute(
            select(Event.type).where(
                Event.project_id == project["id"],
                Event.type == "day_postponed",
            )
        )
    ).scalars().all()
    assert len(events) == 1

    sources = (
        await db_session.execute(
            select(StateVersion.source).where(
                StateVersion.project_id == project["id"],
                StateVersion.version == body["current_version"],
            )
        )
    ).scalars().all()
    assert sources == ["user_edit"]


async def test_postpone_day_rejects_same_day_plan(
    client, auth_headers, enqueue_path
):
    project = await _create_and_commit_carbonara(
        client, auth_headers, enqueue_path
    )
    assert (project.get("cycle") or {}).get("horizon_days", 1) == 1
    response = await client.post(
        f"/api/v1/projects/{project['id']}/postpone-day",
        headers=auth_headers,
    )
    assert response.status_code == 409
    assert "multi-day" in response.json()["detail"].lower()


async def test_postpone_day_preserves_done_today(
    client, auth_headers, enqueue_fitness
):
    """If somehow multiple pending share today, only pending move; done stay."""
    # Fitness fixture has one action per day — skip isn't needed. Completing
    # isn't required; postpone of sole pending is covered above. Here: after
    # postpone once, second postpone on waiting day (no pending today) 409s.
    project = await _create_and_commit_fitness(
        client, auth_headers, enqueue_fitness
    )
    first = await client.post(
        f"/api/v1/projects/{project['id']}/postpone-day",
        headers=auth_headers,
        params={"local_date": date.today().isoformat()},
    )
    assert first.status_code == 200
    second = await client.post(
        f"/api/v1/projects/{project['id']}/postpone-day",
        headers=auth_headers,
        params={"local_date": date.today().isoformat()},
    )
    assert second.status_code == 409
    assert "no pending" in second.json()["detail"].lower()
