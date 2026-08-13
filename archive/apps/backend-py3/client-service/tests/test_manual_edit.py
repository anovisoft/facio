"""Manual editor apply — Slice E2b (checklist / stepper / counter)."""

from copy import deepcopy
from datetime import date

from sqlalchemy import select

from app.models import StateVersion
from tests.conftest import wait_path_ready, wait_plugins_ready
from tests.factories import _sample_train_stepper


async def _create_draft_carbonara(client, auth_headers, enqueue_path) -> dict:
    enqueue_path()
    created = await client.post(
        "/api/v1/projects",
        headers=auth_headers,
        json={"intent": "Приготовить карбонару"},
    )
    return await wait_path_ready(
        client, auth_headers, created.json()["project"]["id"]
    )


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


async def test_manual_edit_checklist_on_draft(
    client, auth_headers, enqueue_path, db_session
):
    project = await _create_draft_carbonara(client, auth_headers, enqueue_path)
    snap = await client.get(
        f"/api/v1/projects/{project['id']}/path-state",
        headers=auth_headers,
    )
    assert snap.status_code == 200
    body = snap.json()
    before_version = body["version"]
    state = body["state"]

    buy = next(a for a in state["actions"] if a["id"] == "buy")
    assert buy["checklist_items"]
    buy["checklist_items"][0]["title"] = "Яйца С0"
    buy["checklist_items"].append(
        {"id": "pepper", "title": "Чёрный перец", "done": False, "sort": 99}
    )

    applied = await client.post(
        f"/api/v1/projects/{project['id']}/manual-edit",
        headers=auth_headers,
        json={"before_version": before_version, "proposed_state": state},
    )
    assert applied.status_code == 200
    detail = applied.json()
    assert detail["undo_version"] == before_version
    assert detail["current_version"] == before_version + 1
    assert detail["status"] == "draft"

    buy_live = next(a for a in detail["actions"] if a["key"] == "buy")
    titles = [c["title"] for c in buy_live["checklist_items"]]
    assert "Яйца С0" in titles
    assert "Чёрный перец" in titles

    sources = (
        await db_session.execute(
            select(StateVersion.source).where(
                StateVersion.project_id == project["id"],
                StateVersion.version == detail["current_version"],
            )
        )
    ).scalars().all()
    assert sources == ["user_edit"]

    # Undo restores prior checklist titles.
    undone = await client.post(
        f"/api/v1/projects/{project['id']}/restore-state",
        headers=auth_headers,
        json={"version": detail["undo_version"]},
    )
    assert undone.status_code == 200
    buy_undone = next(a for a in undone.json()["actions"] if a["key"] == "buy")
    undone_titles = [c["title"] for c in buy_undone["checklist_items"]]
    assert "Яйца С0" not in undone_titles
    assert "Чёрный перец" not in undone_titles


async def test_manual_edit_stepper_and_counter_on_active(
    client, auth_headers, enqueue_fitness
):
    project = await _create_and_commit_fitness(
        client, auth_headers, enqueue_fitness
    )
    snap = await client.get(
        f"/api/v1/projects/{project['id']}/path-state",
        headers=auth_headers,
    )
    assert snap.status_code == 200
    before_version = snap.json()["version"]
    state = snap.json()["state"]

    train = next(a for a in state["actions"] if a["id"] == "d0")
    # Ensure filled stepper (plugins #3); patch targets.
    if not train.get("stepper"):
        train["stepper"] = _sample_train_stepper(measure_target=15)
    for beat in train["stepper"]["beats"]:
        if beat.get("kind") in ("measure", "work") and beat.get("counter"):
            beat["counter"]["target"] = 9
            beat["counter"]["label"] = "reps"

    # Bare action-level counter edit on a rest day action (no stepper).
    rest = next(a for a in state["actions"] if a["id"] == "d1")
    rest["counter"] = {
        "label": "mobility min",
        "target": 12,
        "current": 0,
        "step": 1,
    }

    applied = await client.post(
        f"/api/v1/projects/{project['id']}/manual-edit",
        headers=auth_headers,
        params={"local_date": date.today().isoformat()},
        json={"before_version": before_version, "proposed_state": state},
    )
    assert applied.status_code == 200
    detail = applied.json()
    assert detail["undo_version"] == before_version
    assert detail["status"] == "active"

    d0 = next(a for a in detail["actions"] if a["key"] == "d0")
    assert d0["stepper"] is not None
    work_targets = [
        b["counter"]["target"]
        for b in d0["stepper"]["beats"]
        if b.get("counter")
    ]
    assert work_targets
    assert all(t == 9 for t in work_targets)

    d1 = next(a for a in detail["actions"] if a["key"] == "d1")
    assert d1["counter"] is not None
    assert d1["counter"]["target"] == 12
    assert d1["counter"]["label"] == "mobility min"

    # Session next_action should reflect new stepper targets.
    assert detail["next_action"] is not None
    assert detail["next_action"]["key"] == "d0"
    na_targets = [
        b["counter"]["target"]
        for b in (detail["next_action"].get("stepper") or {}).get("beats", [])
        if b.get("counter")
    ]
    assert na_targets and all(t == 9 for t in na_targets)

    undone = await client.post(
        f"/api/v1/projects/{project['id']}/restore-state",
        headers=auth_headers,
        params={"local_date": date.today().isoformat()},
        json={"version": detail["undo_version"]},
    )
    assert undone.status_code == 200
    d0_undone = next(a for a in undone.json()["actions"] if a["key"] == "d0")
    prior_targets = [
        b["counter"]["target"]
        for b in (d0_undone.get("stepper") or {}).get("beats", [])
        if b.get("counter")
    ]
    assert prior_targets
    assert any(t != 9 for t in prior_targets) or prior_targets == [
        15,
        12,
        12,
    ]


async def test_path_state_version_is_read_only(
    client, auth_headers, enqueue_path
):
    project = await _create_draft_carbonara(client, auth_headers, enqueue_path)
    tip = await client.get(
        f"/api/v1/projects/{project['id']}/path-state",
        headers=auth_headers,
    )
    assert tip.status_code == 200
    version = tip.json()["version"]

    # Mutate tip via manual-edit so tip advances.
    state = tip.json()["state"]
    buy = next(a for a in state["actions"] if a["id"] == "buy")
    buy["checklist_items"][0]["title"] = "Tip eggs"
    applied = await client.post(
        f"/api/v1/projects/{project['id']}/manual-edit",
        headers=auth_headers,
        json={"before_version": version, "proposed_state": state},
    )
    assert applied.status_code == 200
    new_tip = applied.json()["current_version"]

    # Reading the old version does not change tip.
    old = await client.get(
        f"/api/v1/projects/{project['id']}/path-state",
        headers=auth_headers,
        params={"version": version},
    )
    assert old.status_code == 200
    assert old.json()["version"] == version
    old_buy = next(a for a in old.json()["state"]["actions"] if a["id"] == "buy")
    assert old_buy["checklist_items"][0]["title"] != "Tip eggs"

    tip_after = await client.get(
        f"/api/v1/projects/{project['id']}/path-state",
        headers=auth_headers,
    )
    assert tip_after.json()["version"] == new_tip


async def test_manual_edit_rejects_stale_before_version(
    client, auth_headers, enqueue_path
):
    project = await _create_draft_carbonara(client, auth_headers, enqueue_path)
    snap = await client.get(
        f"/api/v1/projects/{project['id']}/path-state",
        headers=auth_headers,
    )
    state = deepcopy(snap.json()["state"])
    buy = next(a for a in state["actions"] if a["id"] == "buy")
    buy["checklist_items"][0]["title"] = "Edited"

    first = await client.post(
        f"/api/v1/projects/{project['id']}/manual-edit",
        headers=auth_headers,
        json={
            "before_version": snap.json()["version"],
            "proposed_state": state,
        },
    )
    assert first.status_code == 200

    stale = await client.post(
        f"/api/v1/projects/{project['id']}/manual-edit",
        headers=auth_headers,
        json={
            "before_version": snap.json()["version"],
            "proposed_state": state,
        },
    )
    assert stale.status_code == 409
