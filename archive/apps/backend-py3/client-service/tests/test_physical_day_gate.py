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
    assert body["undo_version"] == project["current_version"]
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


async def test_repair_preview_then_apply_and_undo_on_active(
    client, auth_headers, enqueue_path, enqueue_repair
):
    """Slice E: Diff preview → confirm apply → Undo on active Guide."""
    project = await _create_and_commit_carbonara(client, auth_headers, enqueue_path)
    before_version = project["current_version"]
    buy_title = next(a["title"] for a in project["actions"] if a["key"] == "buy")

    repaired_state = sample_path_state(
        questions=[],
        paraphrase="Сдвинули готовку на завтра",
    )
    # Visible Diff: rename buy step.
    for action in repaired_state["actions"]:
        if action["id"] == "buy":
            action["title"] = "Купить продукты завтра"
            action["day_offset"] = 1
    repaired_state["cycle"]["horizon_days"] = 2
    repaired_state["days"] = [
        {
            "day_index": 0,
            "kind": "cook_session",
            "title": "Пауза",
            "summary": "",
        },
        {
            "day_index": 1,
            "kind": "cook_session",
            "title": "Вечер готовки",
            "summary": "",
        },
    ]

    enqueue_repair(repaired_state)
    preview = await client.post(
        f"/api/v1/projects/{project['id']}/repair/preview",
        headers=auth_headers,
        json={"intent": "shift"},
    )
    assert preview.status_code == 200
    preview_body = preview.json()
    assert preview_body["before_version"] == before_version
    assert preview_body["summary"] == "Сдвинули готовку на завтра"
    assert preview_body["diff"]
    assert any(
        "завтра" in line["after"].lower() or line["before"] != line["after"]
        for line in preview_body["diff"]
    )
    assert "proposed_state" in preview_body

    # Preview must not bump state version.
    still = await client.get(
        f"/api/v1/projects/{project['id']}",
        headers=auth_headers,
    )
    assert still.json()["current_version"] == before_version

    applied = await client.post(
        f"/api/v1/projects/{project['id']}/repair",
        headers=auth_headers,
        json={
            "intent": "shift",
            "proposed_state": preview_body["proposed_state"],
            "before_version": preview_body["before_version"],
        },
    )
    assert applied.status_code == 200
    applied_body = applied.json()
    assert applied_body["repair_summary"] == "Сдвинули готовку на завтра"
    assert applied_body["undo_version"] == before_version
    assert applied_body["current_version"] == before_version + 1
    assert applied_body["status"] == "active"
    new_buy = next(
        a["title"] for a in applied_body["actions"] if a["key"] == "buy"
    )
    assert new_buy == "Купить продукты завтра"

    undone = await client.post(
        f"/api/v1/projects/{project['id']}/restore-state",
        headers=auth_headers,
        json={"version": applied_body["undo_version"]},
    )
    assert undone.status_code == 200
    undone_body = undone.json()
    assert undone_body["status"] == "active"
    assert undone_body["current_version"] == before_version + 2
    restored_buy = next(
        a["title"] for a in undone_body["actions"] if a["key"] == "buy"
    )
    assert restored_buy == buy_title


async def test_repair_apply_rejects_stale_before_version(
    client, auth_headers, enqueue_path, enqueue_repair
):
    project = await _create_and_commit_carbonara(client, auth_headers, enqueue_path)
    enqueue_repair(
        sample_path_state(questions=[], paraphrase="Сдвинули готовку на завтра")
    )
    preview = await client.post(
        f"/api/v1/projects/{project['id']}/repair/preview",
        headers=auth_headers,
        json={"intent": "shift"},
    )
    assert preview.status_code == 200
    preview_body = preview.json()

    # One-shot repair advances version so preview is stale.
    enqueue_repair(
        sample_path_state(questions=[], paraphrase="Облегчили план")
    )
    raced = await client.post(
        f"/api/v1/projects/{project['id']}/repair",
        headers=auth_headers,
        json={"intent": "lighten"},
    )
    assert raced.status_code == 200

    stale = await client.post(
        f"/api/v1/projects/{project['id']}/repair",
        headers=auth_headers,
        json={
            "intent": "shift",
            "proposed_state": preview_body["proposed_state"],
            "before_version": preview_body["before_version"],
        },
    )
    assert stale.status_code == 409


async def test_repair_lighten_preview_strips_stepper_on_fitness(
    client, auth_headers, enqueue_fitness, enqueue_repair, llm
):
    """lighten must not keep old push-up stepper; rematerialize after apply."""
    from tests.factories import (
        sample_fitness_path_state,
        sample_fitness_plugins_materialize,
    )
    from tests.conftest import wait_plugins_ready

    project = await _create_and_commit_fitness(
        client, auth_headers, enqueue_fitness
    )
    d0_before = next(a for a in project["actions"] if a["key"] == "d0")
    assert d0_before.get("stepper") is not None

    lightened = sample_fitness_path_state(
        questions=[],
        paraphrase="Облегчили сегодняшнюю нагрузку",
    )
    for action in lightened["actions"]:
        if action["id"] == "d0":
            action["title"] = "Лёгкая силовая"
            action["detail"] = "Короче: замер + 1 подход."
        action["stepper"] = None

    enqueue_repair(lightened)
    preview = await client.post(
        f"/api/v1/projects/{project['id']}/repair/preview",
        headers=auth_headers,
        json={"intent": "lighten"},
    )
    assert preview.status_code == 200
    body = preview.json()
    proposed = body["proposed_state"]
    d0 = next(a for a in proposed["actions"] if a.get("id") == "d0")
    assert d0.get("stepper") is None
    assert d0.get("plugin_hints") == ["stepper"]
    assert any(
        line["before"] == "Previous load (sets)" for line in body["diff"]
    )

    llm.enqueue("plugins", sample_fitness_plugins_materialize())
    applied = await client.post(
        f"/api/v1/projects/{project['id']}/repair",
        headers=auth_headers,
        json={
            "intent": "lighten",
            "proposed_state": proposed,
            "before_version": body["before_version"],
        },
    )
    assert applied.status_code == 200
    applied_body = applied.json()
    assert applied_body["plugins_ready"] is False

    ready = await wait_plugins_ready(
        client, auth_headers, project["id"]
    )
    assert ready["plugins_ready"] is True
    d0_after = next(a for a in ready["actions"] if a["key"] == "d0")
    assert d0_after.get("stepper") is not None
