"""The guard that keeps a plain `pytest` from spending money.

Not a hypothetical: the repository root carries a `.env` with
`FACIO_TALK_MODE=live` and a working key, `Settings` reads `.env` relative to
the working directory, and the command in the docs run one directory up is
therefore a paid run that looks identical to the free one.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from facio_api.config import Settings

from support.live import live_opted_in


def test_a_live_env_file_does_not_make_this_run_live(
    tmp_path: Path, request: pytest.FixtureRequest
) -> None:
    """Precedence, pinned: the environment beats the file.

    This is the whole mechanism the session fixture relies on. If
    pydantic-settings ever preferred the file, every non-live run would go live
    on a machine with a live `.env` — and nothing else in the suite would say so.

    Skipped under the opt-in, because that is when the guard deliberately steps
    aside and the file is *supposed* to win. Asserting the guard's effect while
    the guard is off is how `pytest --live` came to fail on its own safety net.
    """
    if live_opted_in(request.config):
        pytest.skip("the guard stands aside under --live; the file is meant to win here")
    env_file = tmp_path / ".env"
    env_file.write_text(
        "FACIO_TALK_MODE=live\nFACIO_ANTHROPIC_API_KEY=sk-ant-not-a-real-key\n",
        encoding="utf-8",
    )
    loaded = Settings(_env_file=str(env_file))

    assert loaded.talk_mode == "scripted"


def test_the_suite_itself_is_scripted(request: pytest.FixtureRequest) -> None:
    if live_opted_in(request.config):
        pytest.skip("live was asked for: the mode is whatever the environment says")
    assert Settings().talk_mode == "scripted"


@pytest.mark.live
def test_the_guard_stands_aside_when_live_was_asked_for(tmp_path: Path) -> None:
    """Only reached with `-m live` / `--live`.

    What «stands aside» means is that a **file** saying live is honoured again —
    not that the process is live by itself. It is not: the documented working
    directory is `apps/api`, which carries no `.env` at all, and the live tests
    load the root one explicitly (`live_env_files`). Asserting the process was
    live was the wrong premise, and it made the paid command red every time.
    """
    env_file = tmp_path / ".env"
    env_file.write_text("FACIO_TALK_MODE=live\n", encoding="utf-8")

    assert Settings(_env_file=str(env_file)).talk_mode == "live"
