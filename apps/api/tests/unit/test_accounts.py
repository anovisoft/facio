from __future__ import annotations

import time
import uuid

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from facio_api.accounts.apple import AppleTokenError, verify_apple_identity_token
from facio_api.accounts.sessions import (
    SessionTokenError,
    create_session_token,
    decode_session_token,
)

BUNDLE_ID = "com.anovisoft.facio"


class _FakeFetcher:
    def __init__(self, key: object) -> None:
        self._key = key

    def signing_key_for(self, token: str) -> object:
        return self._key


@pytest.fixture(scope="module")
def rsa_keys() -> tuple[object, object]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return private_key, private_key.public_key()


def _sign(private_key: object, *, sub: str = "apple-user-1", exp_delta: int = 3600, **extra) -> str:
    now = time.time()
    claims = {
        "iss": "https://appleid.apple.com",
        "aud": BUNDLE_ID,
        "sub": sub,
        "iat": now,
        "exp": now + exp_delta,
        **extra,
    }
    return jwt.encode(claims, private_key, algorithm="RS256")


def test_verify_apple_identity_token_returns_sub_and_email(rsa_keys) -> None:
    private_key, public_key = rsa_keys
    token = _sign(private_key, sub="apple-user-42", email="a@example.com")

    identity = verify_apple_identity_token(
        token, bundle_id=BUNDLE_ID, fetcher=_FakeFetcher(public_key)
    )

    assert identity.sub == "apple-user-42"
    assert identity.email == "a@example.com"


def test_verify_apple_identity_token_rejects_wrong_audience(rsa_keys) -> None:
    private_key, public_key = rsa_keys
    now = time.time()
    token = jwt.encode(
        {
            "iss": "https://appleid.apple.com",
            "aud": "com.someone.else",
            "sub": "apple-user-1",
            "iat": now,
            "exp": now + 3600,
        },
        private_key,
        algorithm="RS256",
    )

    with pytest.raises(AppleTokenError):
        verify_apple_identity_token(token, bundle_id=BUNDLE_ID, fetcher=_FakeFetcher(public_key))


def test_verify_apple_identity_token_rejects_expired_token(rsa_keys) -> None:
    private_key, public_key = rsa_keys
    token = _sign(private_key, exp_delta=-10)

    with pytest.raises(AppleTokenError):
        verify_apple_identity_token(token, bundle_id=BUNDLE_ID, fetcher=_FakeFetcher(public_key))


def test_verify_apple_identity_token_rejects_wrong_key(rsa_keys) -> None:
    private_key, _ = rsa_keys
    other_private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    token = _sign(private_key)

    with pytest.raises(AppleTokenError):
        verify_apple_identity_token(
            token, bundle_id=BUNDLE_ID, fetcher=_FakeFetcher(other_private.public_key())
        )


def test_session_token_round_trips() -> None:
    account_id = uuid.uuid4()
    token = create_session_token(account_id, secret="test-secret")

    decoded = decode_session_token(token, secret="test-secret")

    assert decoded == account_id


def test_session_token_rejects_wrong_secret() -> None:
    account_id = uuid.uuid4()
    token = create_session_token(account_id, secret="test-secret")

    with pytest.raises(SessionTokenError):
        decode_session_token(token, secret="wrong-secret")


def test_session_token_rejects_expired_token() -> None:
    from facio_api.accounts.sessions import SESSION_TTL_SECONDS

    account_id = uuid.uuid4()
    token = create_session_token(
        account_id, secret="test-secret", now=time.time() - SESSION_TTL_SECONDS - 1000
    )

    with pytest.raises(SessionTokenError):
        decode_session_token(token, secret="test-secret")
