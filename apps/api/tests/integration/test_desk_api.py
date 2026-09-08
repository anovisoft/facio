"""Desk sync round-trip against a real Postgres.

The database is built, migrated and dropped by `integration_database` in this
package's conftest, so the run never opens the working desk. Postgres itself
still has to be up (`docker compose up -d postgres`); when it is not, that
fixture skips the package. Nothing else here skips: a database that is up but
misbehaving must fail, or the green means nothing.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from facio_domain.desk import founding_desk

from facio_api.accounts.dependencies import get_current_account
from facio_api.main import app

pytestmark = [
    pytest.mark.integration,
    pytest.mark.usefixtures("integration_database", "fresh_engine_per_event_loop"),
]


@pytest.fixture
async def db_client() -> AsyncIterator[AsyncClient]:
    account_id = uuid.uuid4()
    app.dependency_overrides[get_current_account] = lambda: account_id
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as session:
        yield session
    app.dependency_overrides.pop(get_current_account, None)


async def test_get_missing_desk_is_404(db_client: AsyncClient) -> None:
    response = await db_client.get("/v1/desk")
    assert response.status_code == 404


async def test_desk_requires_a_session(db_client: AsyncClient) -> None:
    app.dependency_overrides.pop(get_current_account, None)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as anon:
        response = await anon.get("/v1/desk")
    assert response.status_code == 401


async def test_put_then_get_round_trips(db_client: AsyncClient) -> None:
    desk = founding_desk().model_dump(mode="json")

    put_response = await db_client.put("/v1/desk", json=desk)
    assert put_response.status_code == 200

    get_response = await db_client.get("/v1/desk")
    assert get_response.status_code == 200
    body = get_response.json()
    assert {s["id"] for s in body["subjects"]} == {"push-ups", "bike", "vegetables"}


async def test_running_progress_survives_a_same_version_structural_write(
    db_client: AsyncClient,
) -> None:
    base = founding_desk().model_dump(mode="json")
    await db_client.put("/v1/desk", json=base)

    running = (await db_client.get("/v1/desk")).json()
    for widget in running["widgets"]:
        if widget["id"] == "push-ups-counter":
            widget["status"] = "running"
            widget["payload"]["count"] = 12
    await db_client.put("/v1/desk", json=running)

    stale = founding_desk().model_dump(mode="json")
    after_stale = (await db_client.put("/v1/desk", json=stale)).json()
    counter = next(w for w in after_stale["widgets"] if w["id"] == "push-ups-counter")
    assert counter["status"] == "running"
    assert counter["payload"]["count"] == 12


async def test_completing_a_widget_clears_stale_running_progress(
    db_client: AsyncClient,
) -> None:
    base = founding_desk().model_dump(mode="json")
    await db_client.put("/v1/desk", json=base)

    running = (await db_client.get("/v1/desk")).json()
    for widget in running["widgets"]:
        if widget["id"] == "push-ups-counter":
            widget["status"] = "running"
            widget["payload"]["count"] = 12
    await db_client.put("/v1/desk", json=running)

    done = (await db_client.get("/v1/desk")).json()
    for widget in done["widgets"]:
        if widget["id"] == "push-ups-counter":
            widget["status"] = "done"
            widget["version"] = 2
            widget["payload"]["count"] = 30
    await db_client.put("/v1/desk", json=done)

    stale = founding_desk().model_dump(mode="json")
    after_stale = (await db_client.put("/v1/desk", json=stale)).json()
    counter = next(w for w in after_stale["widgets"] if w["id"] == "push-ups-counter")
    assert counter["status"] == "done"
    assert counter["payload"]["count"] == 30
