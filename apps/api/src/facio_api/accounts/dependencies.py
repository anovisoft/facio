from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException

from facio_api.accounts.sessions import SessionTokenError, decode_session_token
from facio_api.config import Settings, get_settings

SettingsDep = Annotated[Settings, Depends(get_settings)]


async def get_current_account(
    settings: SettingsDep,
    authorization: Annotated[str | None, Header()] = None,
) -> UUID:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing session token")
    token = authorization.removeprefix("Bearer ").strip()
    try:
        return decode_session_token(token, secret=settings.session_secret)
    except SessionTokenError as error:
        raise HTTPException(status_code=401, detail=str(error)) from error
