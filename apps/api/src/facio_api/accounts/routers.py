from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from facio_api.accounts.apple import AppleTokenError, verify_apple_identity_token
from facio_api.accounts.repository import AccountRepository
from facio_api.accounts.sessions import create_session_token
from facio_api.config import Settings, get_settings
from facio_api.desk.database import get_db

router = APIRouter(prefix="/v1/auth", tags=["accounts"])

SettingsDep = Annotated[Settings, Depends(get_settings)]
SessionDep = Annotated[AsyncSession, Depends(get_db)]


class AppleSignInRequest(BaseModel):
    identity_token: str


class AppleSignInResponse(BaseModel):
    account_id: str
    session_token: str


@router.post("/apple")
async def sign_in_with_apple(
    body: AppleSignInRequest, settings: SettingsDep, session: SessionDep
) -> AppleSignInResponse:
    try:
        identity = verify_apple_identity_token(
            body.identity_token, bundle_id=settings.apple_bundle_id
        )
    except AppleTokenError as error:
        raise HTTPException(status_code=401, detail=str(error)) from error

    account = await AccountRepository(session).get_or_create_by_apple_sub(
        identity.sub, email=identity.email
    )
    token = create_session_token(account.id, secret=settings.session_secret)
    return AppleSignInResponse(account_id=str(account.id), session_token=token)
