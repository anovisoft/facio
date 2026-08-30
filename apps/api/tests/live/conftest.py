"""Live-only: skip unless opted in; build a live provider from env keys."""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from datetime import datetime
from typing import Any

import pytest

from facio_domain.desk import founding_desk
from facio_domain.models import Desk

from facio_api.config import Settings
from facio_api.providers.factory import provider_for
from facio_api.talk.loop import run_turn
from facio_api.talk.schemas import (
    Locale,
    TalkSelection,
    TalkTurnRequest,
    TalkTurnResponse,
    ThreadMessage,
)
from support.live import (
    LIVE_OPT_IN_REASON,
    force_live,
    live_env_files,
    live_opted_in,
    skip_without_vendor_key,
)

NOW = datetime(2026, 8, 15, 12, 0, 0)

LivePlay = Callable[..., Coroutine[Any, Any, TalkTurnResponse]]


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if live_opted_in(config):
        return
    skip = pytest.mark.skip(reason=LIVE_OPT_IN_REASON)
    for item in items:
        if item.get_closest_marker("live"):
            item.add_marker(skip)


@pytest.fixture
def live_settings() -> Settings:
    files = live_env_files()
    loaded = Settings(_env_file=files or None)
    return skip_without_vendor_key(force_live(loaded))


def _play_for(live_settings: Settings, locale: Locale) -> LivePlay:
    async def play(
        utterance: str,
        selection: TalkSelection | None = None,
        *,
        focused_widget_id: str | None = None,
        desk: Desk | None = None,
        thread: list[ThreadMessage] | None = None,
    ) -> TalkTurnResponse:
        """`desk` and `thread` carry a previous turn in, for a second utterance
        that only makes sense on what the first one wrote and said. «Их» has an
        antecedent on a real phone; a turn sent without one is a different
        question."""
        provider = provider_for(live_settings, utterance)
        request = TalkTurnRequest(
            utterance=utterance,
            desk=desk if desk is not None else founding_desk(now=NOW),
            thread=thread or [],
            thread_id=f"live-{locale}",
            now=NOW,
            locale=locale,
            selection=selection,
            focused_widget_id=focused_widget_id,
        )
        return await run_turn(request, provider, now=NOW)

    return play


@pytest.fixture
def live_play(live_settings: Settings) -> LivePlay:
    return _play_for(live_settings, "ru")


@pytest.fixture
def live_play_en(live_settings: Settings) -> LivePlay:
    return _play_for(live_settings, "en")
