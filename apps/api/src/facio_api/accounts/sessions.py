"""Our own session token — issued once we've verified an Apple identity
token, not a second identity system. HS256, short claim set, no refresh
table for v1 (the client re-runs Sign in with Apple to get a new one)."""

from __future__ import annotations

import time
from uuid import UUID

import jwt

SESSION_TTL_SECONDS = 30 * 24 * 60 * 60  # 30 days
ALGORITHM = "HS256"


class SessionTokenError(ValueError):
    pass


def create_session_token(account_id: UUID, *, secret: str, now: float | None = None) -> str:
    issued_at = now if now is not None else time.time()
    claims = {"sub": str(account_id), "iat": issued_at, "exp": issued_at + SESSION_TTL_SECONDS}
    return jwt.encode(claims, secret, algorithm=ALGORITHM)


def decode_session_token(token: str, *, secret: str) -> UUID:
    try:
        claims = jwt.decode(token, secret, algorithms=[ALGORITHM])
    except jwt.PyJWTError as error:
        raise SessionTokenError(str(error)) from error
    try:
        return UUID(claims["sub"])
    except (KeyError, ValueError) as error:
        raise SessionTokenError("session token has no valid sub") from error
