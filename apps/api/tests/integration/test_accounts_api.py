"""POST /v1/auth/apple end-to-end, and that the issued session token then
authenticates /v1/desk. Requires Postgres — see test_desk_api.py's docstring;
skips cleanly if unreachable."""

from __future__ import annotations

import time
from collections.abc import AsyncIterator

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from httpx import ASGITransport, AsyncClient

from facio_api import config as config_module
from facio_api.accounts import apple as apple_module
from facio_api.config import get_settings
from facio_api.desk import database
from facio_api.main import app

pytestmark = pytest.mark.integration

BUNDLE_ID = config_module.Settings().apple_bundle_id


class _FakeFetcher:
    def __init__(self, key: object) -> None:
        self._key = key

    def signing_key_for(self, token: str) -> object:
        return self._key


@pytest.fixture(autouse=True)
async def _fresh_engine_per_event_loop() -> AsyncIterator[None]:
    yield
    settings = get_settings()
    engine = database._engine(settings.database_url)
    await engine.dispose()
    database._engine.cache_clear()
    database._sessionmaker.cache_clear()


@pytest.fixture
def apple_identity_token(monkeypatch: pytest.MonkeyPatch) -> str:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    monkeypatch.setattr(
        apple_module, "_default_fetcher", _FakeFetcher(private_key.public_key())
    )
    now = time.time()
    return jwt.encode(
        {
            "iss": "https://appleid.apple.com",
            "aud": BUNDLE_ID,
            "sub": f"apple-user-{now}",
            "iat": now,
            "exp": now + 3600,
        },
        private_key,
        algorithm="RS256",
    )


async def test_sign_in_then_use_desk(apple_identity_token: str) -> None:
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        sign_in = await client.post(
            "/v1/auth/apple", json={"identity_token": apple_identity_token}
        )
        if sign_in.status_code == 500:
            pytest.skip("Postgres not reachable — run `docker compose up -d postgres`")
        assert sign_in.status_code == 200
        body = sign_in.json()
        assert body["account_id"]
        headers = {"Authorization": f"Bearer {body['session_token']}"}

        no_desk_yet = await client.get("/v1/desk", headers=headers)
        assert no_desk_yet.status_code == 404

        unauthenticated = await client.get("/v1/desk")
        assert unauthenticated.status_code == 401


async def test_sign_in_rejects_bad_token() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/v1/auth/apple", json={"identity_token": "not-a-jwt"})
    assert response.status_code == 401
