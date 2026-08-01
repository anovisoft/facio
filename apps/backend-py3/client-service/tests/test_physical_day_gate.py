"""Physical-day gate + Repair intents (Slice 4): API-level behavior.

See docs/next/04-model.md §4 (Физический день) + §8 (Repair) and
docs/next/09-continuity.md decisions A / E.
"""

from datetime import date, timedelta

from tests.conftest import wait_path_ready, wait_plugins_ready
from tests.factories import sample_path_state


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


async def test_commit_persists_cycle_anchor_date(
    client, auth_headers, enqueue_fitness
):
    project = await _create_and_commit_fitness(
        client, auth_headers, enqueue_fitness
    )
    assert project["cycle_anchor_date"] == date.today().isoformat()
    assert project["unlocked_day_index"] == 0


async def test_commit_tomorrow_shifts_anchor_date(
    client, auth_headers, enqueue_fitness
):
    project = await _create_and_commit_fitness(
        client, auth_headers, enqueue_fitness, first_step_when="tomorrow"
    )
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    assert project["cycle_anchor_date"] == tomorrow
    # Before anchor: nothing executable; day 0 is peek-only until tomorrow.
    assert project["unlocked_day_index"] == -1
    assert project["next_action"] is None
    assert project["peek_action"] is not None
    assert project["peek_action"]["day_offset"] == 0
    assert project["peek_action"]["day_locked"] is True
    assert project["next_unlock_date"] == tomorrow


async def test_future_days_are_visible_but_locked(
    client, auth_headers, enqueue_fitness
):
    project = await _create_and_commit_fitness(
        client, auth_headers, enqueue_fitness
    )
    # Preview (must): every day is still present in the actions list.
    day_offsets = {a["day_offset"] for a in project["actions"]}
    assert day_offsets == {0, 1, 2, 3, 4, 5, 6}
    for action in project["actions"]:
        assert action["day_locked"] == (action["day_offset"] > 0)


async def test_complete_rejected_on_locked_future_day(
    client, auth_headers, enqueue_fitness
):
    project = await _create_and_commit_fitness(
        client, auth_headers, enqueue_fitness
    )
    d1 = next(a for a in project["actions"] if a["key"] == "d1")
    assert d1["day_locked"] is True

    response = await client.post(
        f"/api/v1/actions/{d1['id']}/complete", headers=auth_headers
    )
    assert response.status_code == 409
    assert "day" in response.json()["detail"].lower()

    skip_response = await client.post(
        f"/api/v1/actions/{d1['id']}/skip", headers=auth_headers
    )
    assert skip_response.status_code == 409


async def test_completing_today_does_not_unlock_tomorrow_early(
    client, auth_headers, enqueue_fitness
):
    """DoD #1: finishing day N early must not let day N+1 execute today."""
    project = await _create_and_commit_fitness(
        client, auth_headers, enqueue_fitness
    )
    d0 = next(a for a in project["actions"] if a["key"] == "d0")
    completed = await client.post(
        f"/api/v1/actions/{d0['id']}/complete", headers=auth_headers
    )
    assert completed.status_code == 200

    detail = await client.get(
        f"/api/v1/projects/{project['id']}", headers=auth_headers
    )
    body = detail.json()
    assert body["unlocked_day_index"] == 0
    assert body["next_action"] is None
    assert body["peek_action"]["key"] == "d1"
    assert body["peek_action"]["day_locked"] is True

    d1 = body["peek_action"]
    still_locked = await client.post(
        f"/api/v1/actions/{d1['id']}/complete", headers=auth_headers
    )
    assert still_locked.status_code == 409


async def test_local_date_query_param_unlocks_next_day(
    client, auth_headers, enqueue_fitness
):
    project = await _create_and_commit_fitness(
        client, auth_headers, enqueue_fitness
    )
    anchor = date.fromisoformat(project["cycle_anchor_date"])
    tomorrow = (anchor + timedelta(days=1)).isoformat()

    detail = await client.get(
        f"/api/v1/projects/{project['id']}",
        headers=auth_headers,
        params={"local_date": tomorrow},
    )
    body = detail.json()
    assert body["unlocked_day_index"] == 1
    # Catch-up: day 0 (d0) is still pending, so focus stays there.
    assert body["next_action"]["key"] == "d0"

    d0 = body["next_action"]
    completed = await client.post(
        f"/api/v1/actions/{d0['id']}/complete",
        headers=auth_headers,
        params={"local_date": tomorrow},
    )
    assert completed.status_code == 200

    detail2 = await client.get(
        f"/api/v1/projects/{project['id']}",
        headers=auth_headers,
        params={"local_date": tomorrow},
    )
    body2 = detail2.json()
    assert body2["next_action"]["key"] == "d1"
    assert body2["next_action"]["day_locked"] is False

    completed_d1 = await client.post(
        f"/api/v1/actions/{body2['next_action']['id']}/complete",
        headers=auth_headers,
        params={"local_date": tomorrow},
    )
    assert completed_d1.status_code == 200


async def test_local_date_rejects_bad_format(
    client, auth_headers, enqueue_fitness
):
    project = await _create_and_commit_fitness(
        client, auth_headers, enqueue_fitness
    )
    response = await client.get(
        f"/api/v1/projects/{project['id']}",
        headers=auth_headers,
        params={"local_date": "31/07/2026"},
    )
    assert response.status_code == 422


async def test_carbonara_horizon_one_never_regresses(
    client, auth_headers, enqueue_path
):
    """DoD #4: horizon_days=1 stays unlocked=0 regardless of local_date."""
    project = await _create_and_commit_carbonara(client, auth_headers, enqueue_path)
    assert project["unlocked_day_index"] == 0

    far_future = (date.today() + timedelta(days=30)).isoformat()
    detail = await client.get(
        f"/api/v1/projects/{project['id']}",
        headers=auth_headers,
        params={"local_date": far_future},
    )
    body = detail.json()
    assert body["unlocked_day_index"] == 0
    assert body["next_action"]["key"] == "buy"
    for action in body["actions"]:
        assert action["day_locked"] is False


async def test_repair_requires_intent_or_reason(
    client, auth_headers, enqueue_path
):
    project = await _create_and_commit_carbonara(client, auth_headers, enqueue_path)
    response = await client.post(
        f"/api/v1/projects/{project['id']}/repair",
        headers=auth_headers,
        json={},
    )
    assert response.status_code == 422


async def test_repair_with_intent_only_returns_summary(
    client, auth_headers, enqueue_path, enqueue_repair
):
    project = await _create_and_commit_carbonara(client, auth_headers, enqueue_path)
    enqueue_repair(
        sample_path_state(questions=[], paraphrase="Сдвинули готовку на завтра")
    )
    response = await client.post(
        f"/api/v1/projects/{project['id']}/repair",
        headers=auth_headers,
        json={"intent": "shift"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["repair_summary"] == "Сдвинули готовку на завтра"
    # Repair must not unlock future execute incorrectly: anchor stays fixed.
    assert body["cycle_anchor_date"] == project["cycle_anchor_date"]


async def test_repair_lighten_intent_reaches_llm(
    client, auth_headers, enqueue_path, enqueue_repair, llm
):
    project = await _create_and_commit_carbonara(client, auth_headers, enqueue_path)
    enqueue_repair(sample_path_state(questions=[], paraphrase="Облегчили план"))
    response = await client.post(
        f"/api/v1/projects/{project['id']}/repair",
        headers=auth_headers,
        json={"intent": "lighten", "reason": "устал"},
    )
    assert response.status_code == 200
    assert response.json()["repair_summary"] == "Облегчили план"

    repair_call = next(c for c in llm.calls if c["purpose"] == "repair")
    user_message = repair_call["messages"][-1]["content"]
    assert "lighten" in user_message
    assert "устал" in user_message


async def test_repair_rest_intent_still_returns_new_today(
    client, auth_headers, enqueue_path, enqueue_repair
):
    project = await _create_and_commit_carbonara(client, auth_headers, enqueue_path)
    enqueue_repair(
        sample_path_state(questions=[], paraphrase="Заменили на день отдыха")
    )
    response = await client.post(
        f"/api/v1/projects/{project['id']}/repair",
        headers=auth_headers,
        json={"intent": "rest"},
    )
    assert response.status_code == 200
    body = response.json()
    # DoD #3: no project recreate — same project id, still active, has a
    # sensible Today (next_action derived fresh from the repaired state).
    assert body["id"] == project["id"]
    assert body["status"] == "active"
    assert body["next_action"] is not None
