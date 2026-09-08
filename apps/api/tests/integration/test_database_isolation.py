"""The lock that keeps this hole shut.

The hole was never a bug in a test: it was that nothing anywhere said which
database the integration package is allowed to open, so the default — the
working one — was as acceptable as any. These two tests say it. If the fixture
in `conftest.py` is removed, weakened, or quietly bypassed, the package goes
red here instead of going green on top of the phone's rows.

Both halves are needed. The first reads the settings the app is handed; the
second asks the database itself what its name is, because settings that say
one thing while `get_db` opens another is precisely the failure that would
otherwise pass unnoticed.
"""

from __future__ import annotations

import pytest
from sqlalchemy import text

from facio_api.config import get_settings
from facio_api.desk.database import get_db

from support.database import TEST_DATABASE_PREFIX, is_test_database

pytestmark = [
    pytest.mark.integration,
    pytest.mark.usefixtures("integration_database", "fresh_engine_per_event_loop"),
]


def test_settings_point_at_a_throwaway_database() -> None:
    url = get_settings().database_url
    assert is_test_database(url), (
        f"integration run is pointed at {url!r}; the database name must start "
        f"with {TEST_DATABASE_PREFIX!r} so a run can never write to the working desk"
    )


async def test_the_session_the_app_gets_lands_in_that_database() -> None:
    settings = get_settings()
    async for session in get_db(settings):
        name = await session.scalar(text("SELECT current_database()"))

    assert name is not None and name.startswith(TEST_DATABASE_PREFIX), (
        f"a request would have written to database {name!r}"
    )
