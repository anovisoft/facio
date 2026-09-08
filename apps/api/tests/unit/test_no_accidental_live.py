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


def test_a_live_env_file_does_not_make_this_run_live(tmp_path: Path) -> None:
    """Precedence, pinned: the environment beats the file.

    This is the whole mechanism the session fixture relies on. If
    pydantic-settings ever preferred the file, every non-live run would go live
    on a machine with a live `.env` — and nothing else in the suite would say so.
    """
    env_file = tmp_path / ".env"
    env_file.write_text(
        "FACIO_TALK_MODE=live\nFACIO_ANTHROPIC_API_KEY=sk-ant-not-a-real-key\n",
        encoding="utf-8",
    )
    loaded = Settings(_env_file=str(env_file))

    assert loaded.talk_mode == "scripted"


def test_the_suite_itself_is_scripted() -> None:
    assert Settings().talk_mode == "scripted"


@pytest.mark.live
def test_the_guard_stands_aside_when_live_was_asked_for() -> None:
    """Only reached with `-m live` / `--live`, and then the mode is the env's
    again — otherwise opting in would be opted back out by the guard."""
    assert Settings().talk_mode == "live"
