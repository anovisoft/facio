"""What counts as a throwaway test database. No connection, no side effects.

The name is the whole safety story: the integration package may only ever look
at a database whose name says out loud that it is disposable, and the teardown
may only ever drop such a name. Both the fixture that builds the database and
the lock test that refuses the working one read the rule from here, so there is
one definition of "test database" and not two that can drift apart.
"""

from __future__ import annotations

import os
import uuid

from sqlalchemy.engine import URL, make_url

TEST_DATABASE_PREFIX = "facio_test_"


def new_test_database_name() -> str:
    """A name no other run can be holding: this process, plus a fresh id.

    The pid alone is not enough — pids come back around, and two runs a minute
    apart can collide on a machine that has been up a while.
    """
    return f"{TEST_DATABASE_PREFIX}{os.getpid()}_{uuid.uuid4().hex[:8]}"


def is_test_database(url: str | URL) -> bool:
    """True only for a database whose name is marked as throwaway."""
    database = make_url(str(url)).database
    return bool(database) and database.startswith(TEST_DATABASE_PREFIX)
