"""Opt-in and skip helpers for live vendor tests. No network."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from facio_api.config import Settings, UnknownModelError

LIVE_OPT_IN_REASON = "opt in: pytest -m live"


def live_env_files() -> tuple[str, ...]:
    """Root `.env` then `apps/api/.env` (later wins). Missing files omitted."""
    here = Path(__file__).resolve()
    api_root = here.parents[2]
    repo_root = here.parents[4]
    paths = [repo_root / ".env", api_root / ".env"]
    return tuple(str(path) for path in paths if path.is_file())


def live_opted_in(config: Any) -> bool:
    """True when the run asked for live: `--live` or `-m live` (exact)."""
    flag = bool(config.getoption("--live"))
    markexpr = (getattr(config.option, "markexpr", None) or "").strip()
    return flag or markexpr == "live"


def force_live(settings: Settings) -> Settings:
    """Keep model and keys; ignore env `talk_mode=scripted`."""
    return settings.model_copy(update={"talk_mode": "live"})


def skip_without_vendor_key(settings: Settings) -> Settings:
    """Skip when the selected family has no key. Never prints the key."""
    try:
        family = settings.family
    except UnknownModelError:
        pytest.skip("unknown FACIO_MODEL_NAME family")
    if not settings.key_for(family):
        pytest.skip(f"{family} key missing")
    return settings
