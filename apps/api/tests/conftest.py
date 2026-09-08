from __future__ import annotations

import os
from collections.abc import AsyncIterator, Iterator

import pytest
from httpx import ASGITransport, AsyncClient

from facio_api.config import Settings, get_settings
from facio_api.main import app

from support.live import LIVE_OPT_IN_REASON, live_opted_in


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--live",
        action="store_true",
        default=False,
        help="run live vendor invariant tests",
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Skip every `live` test unless it was asked for — wherever it lives.

    This hook used to sit in `tests/live/conftest.py`, where pytest applies it
    only to items in that directory: a test marked `live` anywhere else ran
    unguarded against a real vendor. One hook at the root, so the marker means
    the same thing in every file.
    """
    if live_opted_in(config):
        return
    skip = pytest.mark.skip(reason=LIVE_OPT_IN_REASON)
    for item in items:
        if item.get_closest_marker("live"):
            item.add_marker(skip)


@pytest.fixture(scope="session", autouse=True)
def no_vendor_unless_asked(request: pytest.FixtureRequest) -> Iterator[None]:
    """A run nobody asked to be live cannot reach a vendor.

    `Settings` reads `.env` **relative to the working directory**, and the
    repository root holds one with `FACIO_TALK_MODE=live` and a real key in it.
    So the documented command run one directory up is a paid run, and it looks
    exactly like the free one until the bill arrives. The opt-in for spending
    money is `-m live` / `--live` and nothing else; without it the mode is
    pinned here, in the environment, which takes precedence over any file.

    Live tests are unaffected: they are skipped without the opt-in, and with it
    this fixture stands aside. The keys themselves are left alone — `scripted`
    never reaches a provider that would use one, and blanking them here would
    only fall back to the file (`env_ignore_empty`).
    """
    if live_opted_in(request.config):
        yield
        return
    previous = os.environ.get("FACIO_TALK_MODE")
    os.environ["FACIO_TALK_MODE"] = "scripted"
    get_settings.cache_clear()
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop("FACIO_TALK_MODE", None)
        else:
            os.environ["FACIO_TALK_MODE"] = previous
        get_settings.cache_clear()


@pytest.fixture
def settings() -> Settings:
    return Settings(
        talk_mode="scripted",
        model_name="gpt-4o-mini",
        openai_api_key=None,
        anthropic_api_key=None,
    )


@pytest.fixture
async def client(settings: Settings) -> AsyncIterator[AsyncClient]:
    app.dependency_overrides[get_settings] = lambda: settings
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as session:
        yield session
    app.dependency_overrides.clear()
