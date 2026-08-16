from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from facio_api.config import Settings, get_settings
from facio_api.main import app


@pytest.fixture
def settings() -> Settings:
    return Settings(talk_mode="scripted", model_api_key=None)


@pytest.fixture
async def client(settings: Settings) -> AsyncIterator[AsyncClient]:
    app.dependency_overrides[get_settings] = lambda: settings
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as session:
        yield session
    app.dependency_overrides.clear()
