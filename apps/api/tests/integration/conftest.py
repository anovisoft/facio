"""One throwaway database per integration run, dropped when the run ends.

The package used to open whatever `FACIO_DATABASE_URL` named, and the default
names the working database of the local compose stack — the same rows the phone
reads. Every run signed in a fresh Apple account and stored a desk there. That
is tolerable while the only inhabitants are synthetic; it is not tolerable in a
database that is about to hold real people. So the run now builds its own
`facio_test_…` database on that same server, migrates it with alembic, points
`Settings` at it for the whole package, and drops it afterwards — including
when a test failed, because a failed run is exactly when the leftovers pile up.

The skip stays honest. "Postgres is not running" is the one condition CI knows
about, and it still skips the package. A server that answers but a database
that will not prepare is a **failure**: skipping there would paint a package
green that never ran.

The database is created and dropped from the maintenance database, never from
the working one and never from the database being dropped, and the drop refuses
any name that is not marked throwaway (`support.database`).
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import create_async_engine

from facio_api.config import Settings, get_settings
from facio_api.desk import database

from support.database import is_test_database, new_test_database_name

API_ROOT = Path(__file__).resolve().parents[2]

# CREATE DATABASE / DROP DATABASE cannot run from inside the database they name,
# and must not run from the working one — a stray transaction there is the thing
# this whole file exists to avoid.
MAINTENANCE_DATABASE = "postgres"

DATABASE_URL_ENV = "FACIO_DATABASE_URL"

POSTGRES_DOWN = "Postgres not reachable — run `docker compose up -d postgres`"


async def _execute(url: URL, statements: tuple[str, ...]) -> None:
    """Run DDL with autocommit: CREATE/DROP DATABASE refuse a transaction block."""
    engine = create_async_engine(url, isolation_level="AUTOCOMMIT")
    try:
        async with engine.connect() as connection:
            for statement in statements:
                await connection.execute(text(statement))
    finally:
        await engine.dispose()


def _reachable(url: URL) -> bool:
    """A refused socket is "no Postgres here"; anything else is a real fault.

    asyncpg lets the plain `OSError` through rather than wrapping it, so bad
    credentials or a missing maintenance database raise something else and
    travel on up as a failure instead of a quiet skip.
    """
    try:
        asyncio.run(_execute(url, ("SELECT 1",)))
    except OSError:
        return False
    return True


def _migrate(url: URL) -> None:
    """`alembic upgrade head` on the fresh database.

    `alembic/env.py` reads the URL from `get_settings()`, which the caller has
    already pointed at this database; the explicit option is there so the
    migration cannot land anywhere else if env.py ever stops doing that.
    """
    config = Config(str(API_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(API_ROOT / "alembic"))
    config.set_main_option("sqlalchemy.url", url.render_as_string(hide_password=False))
    command.upgrade(config, "head")


def _forget_engines() -> None:
    """Drop the URL-keyed engine cache so the next session opens the new URL."""
    database._engine.cache_clear()
    database._sessionmaker.cache_clear()


@pytest.fixture(scope="session")
def integration_database() -> Iterator[str]:
    configured = make_url(Settings().database_url)
    server = configured.set(database=MAINTENANCE_DATABASE)

    if not _reachable(server):
        pytest.skip(POSTGRES_DOWN)

    name = new_test_database_name()
    target = configured.set(database=name)
    if not is_test_database(target):
        raise AssertionError(f"refusing to run against {name!r}: not a test database")

    previous = os.environ.get(DATABASE_URL_ENV)
    asyncio.run(_execute(server, (f'CREATE DATABASE "{name}"',)))
    try:
        # Settings is the single source the app, the repositories and env.py all
        # read, so the swap happens once, here, rather than at every call site.
        os.environ[DATABASE_URL_ENV] = target.render_as_string(hide_password=False)
        get_settings.cache_clear()
        _forget_engines()
        _migrate(target)
        yield name
    finally:
        if previous is None:
            os.environ.pop(DATABASE_URL_ENV, None)
        else:
            os.environ[DATABASE_URL_ENV] = previous
        get_settings.cache_clear()
        _forget_engines()
        # The name is generated above, so this can only fire if someone changes
        # how it is built; a DROP is not a statement to take on trust.
        if not is_test_database(target):
            raise AssertionError(f"refusing to drop {name!r}: not a test database")
        # FORCE: a test that failed mid-request can leave a connection open, and
        # a database that will not drop is the leftover we came here to remove.
        asyncio.run(_execute(server, (f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)',)))


@pytest.fixture
async def fresh_engine_per_event_loop() -> AsyncIterator[None]:
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
    _forget_engines()
