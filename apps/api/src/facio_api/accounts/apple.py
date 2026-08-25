"""Verify a Sign in with Apple identity token.

Not generic JWT users: there is no password and no `OAuth2PasswordBearer`.
This only checks a token Apple already signed and hands back the `sub`
(Apple's stable per-app user id) — `accounts/routers.py` turns that into our
own account and our own session token.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import httpx
import jwt
from jwt import PyJWKClient

APPLE_ISSUER = "https://appleid.apple.com"
APPLE_JWKS_URL = "https://appleid.apple.com/auth/keys"


class AppleTokenError(ValueError):
    """The identity token failed signature, issuer, audience, or expiry checks."""


@dataclass(frozen=True)
class AppleIdentity:
    sub: str
    email: str | None


class JWKSFetcher:
    """Wraps `PyJWKClient` behind a swappable interface so tests can inject a
    fake key set instead of calling Apple's real JWKS endpoint."""

    def __init__(self, jwks_url: str = APPLE_JWKS_URL) -> None:
        self._client = PyJWKClient(jwks_url)

    def signing_key_for(self, token: str) -> str:
        return self._client.get_signing_key_from_jwt(token).key


_default_fetcher = JWKSFetcher()


def verify_apple_identity_token(
    token: str,
    *,
    bundle_id: str,
    fetcher: JWKSFetcher | None = None,
    now: float | None = None,
) -> AppleIdentity:
    try:
        signing_key = (fetcher or _default_fetcher).signing_key_for(token)
        claims = jwt.decode(
            token,
            key=signing_key,
            algorithms=["RS256"],
            audience=bundle_id,
            issuer=APPLE_ISSUER,
        )
    except jwt.PyJWTError as error:
        raise AppleTokenError(str(error)) from error

    exp = claims.get("exp")
    if exp is not None and exp < (now if now is not None else time.time()):
        raise AppleTokenError("identity token expired")

    sub = claims.get("sub")
    if not sub:
        raise AppleTokenError("identity token has no sub")
    return AppleIdentity(sub=sub, email=claims.get("email"))


def fetch_jwks(jwks_url: str = APPLE_JWKS_URL) -> dict:
    """Used only by tests/tools that want the raw key set, not by the
    verification path above (which streams through `PyJWKClient`)."""
    response = httpx.get(jwks_url, timeout=5.0)
    response.raise_for_status()
    return response.json()
