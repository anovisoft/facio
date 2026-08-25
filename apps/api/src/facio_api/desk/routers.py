"""Desk sync endpoints. Account comes from the session token (В3.1/M2)."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from facio_domain.models import Desk

from facio_api.accounts.dependencies import get_current_account
from facio_api.desk.database import get_db
from facio_api.desk.repository import DeskRepository

router = APIRouter(prefix="/v1/desk", tags=["desk"])

SessionDep = Annotated[AsyncSession, Depends(get_db)]
AccountDep = Annotated[UUID, Depends(get_current_account)]


@router.get("")
async def get_desk(account_id: AccountDep, session: SessionDep) -> Desk:
    desk = await DeskRepository(session).load(account_id)
    if desk is None:
        raise HTTPException(status_code=404, detail="no desk stored for this account")
    return desk


@router.put("")
async def put_desk(desk: Desk, account_id: AccountDep, session: SessionDep) -> Desk:
    return await DeskRepository(session).merge_and_save(account_id, desk)
