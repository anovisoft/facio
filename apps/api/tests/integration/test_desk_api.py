"""Desk sync round-trip against a real Postgres.

Requires `docker compose up -d postgres` (or any reachable
`FACIO_DATABASE_URL`) with `alembic upgrade head` applied — see
apps/api/README or docs/state/plan.md M1. Skips cleanly if the database
isn't reachable, so a plain `pytest` run without Postgres stays green.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from facio_domain.desk import founding_desk

from facio_api.config import get_settings
from facio_api.desk import database
from facio_api.main import app

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
async def _fresh_engine_per_event_loop() -> AsyncIterator[None]:
    # The engine cache is keyed by URL and lives across tests, but each test
    # function gets its own asyncio event loop (pytest-asyncio default scope)
    # and asyncpg connections are bound to the loop they were opened on —
    # reusing a cached engine across loops raises "attached to a different
    # loop". Dispose the engine on this test's loop and drop the cache after
    # every test so the next test builds a fresh one on its own loop.
    yield
    settings = get_settings()
    engine = database._engine(settings.database_url)
    await engine.dispose()
    database._engine.cache_clear()
    database._sessionmaker.cache_clear()


@pytest.fixture
async def db_client() -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as session:
        # Probe once before handing the client to the test — skip if no DB.
        try:
            probe = await session.get(f"/v1/desk/{uuid.uuid4()}")
        except Exception:  # noqa: BLE001 - any connection failure means "skip"
            pytest.skip("Postgres not reachable — run `docker compose up -d postgres`")
        if probe.status_code == 500:
            pytest.skip("Postgres not reachable — run `docker compose up -d postgres`")
        yield session


async def test_get_missing_desk_is_404(db_client: AsyncClient) -> None:
    response = await db_client.get(f"/v1/desk/{uuid.uuid4()}")
    assert response.status_code == 404


async def test_put_then_get_round_trips(db_client: AsyncClient) -> None:
    account_id = uuid.uuid4()
    desk = founding_desk().model_dump(mode="json")

    put_response = await db_client.put(f"/v1/desk/{account_id}", json=desk)
    assert put_response.status_code == 200

    get_response = await db_client.get(f"/v1/desk/{account_id}")
    assert get_response.status_code == 200
    body = get_response.json()
    assert {s["id"] for s in body["subjects"]} == {"push-ups", "bike", "vegetables"}


async def test_running_progress_survives_a_same_version_structural_write(
    db_client: AsyncClient,
) -> None:
    account_id = uuid.uuid4()
    base = founding_desk().model_dump(mode="json")
    await db_client.put(f"/v1/desk/{account_id}", json=base)

    running = (await db_client.get(f"/v1/desk/{account_id}")).json()
    for widget in running["widgets"]:
        if widget["id"] == "push-ups-counter":
            widget["status"] = "running"
            widget["payload"]["count"] = 12
    await db_client.put(f"/v1/desk/{account_id}", json=running)

    stale = founding_desk().model_dump(mode="json")
    after_stale = (await db_client.put(f"/v1/desk/{account_id}", json=stale)).json()
    counter = next(w for w in after_stale["widgets"] if w["id"] == "push-ups-counter")
    assert counter["status"] == "running"
    assert counter["payload"]["count"] == 12


async def test_completing_a_widget_clears_stale_running_progress(
    db_client: AsyncClient,
) -> None:
    account_id = uuid.uuid4()
    base = founding_desk().model_dump(mode="json")
    await db_client.put(f"/v1/desk/{account_id}", json=base)

    running = (await db_client.get(f"/v1/desk/{account_id}")).json()
    for widget in running["widgets"]:
        if widget["id"] == "push-ups-counter":
            widget["status"] = "running"
            widget["payload"]["count"] = 12
    await db_client.put(f"/v1/desk/{account_id}", json=running)

    done = (await db_client.get(f"/v1/desk/{account_id}")).json()
    for widget in done["widgets"]:
        if widget["id"] == "push-ups-counter":
            widget["status"] = "done"
            widget["version"] = 2
            widget["payload"]["count"] = 30
    await db_client.put(f"/v1/desk/{account_id}", json=done)

    stale = founding_desk().model_dump(mode="json")
    after_stale = (await db_client.put(f"/v1/desk/{account_id}", json=stale)).json()
    counter = next(w for w in after_stale["widgets"] if w["id"] == "push-ups-counter")
    assert counter["status"] == "done"
    assert counter["payload"]["count"] == 30
