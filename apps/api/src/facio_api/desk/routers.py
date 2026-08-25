"""Desk sync endpoints.

`account_id` is a path parameter here because accounts (В3.1/M2 — Sign in with
Apple) land after this milestone. M2 replaces the path parameter with a
`get_current_account` dependency derived from the session token; the
repository call underneath does not change.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from facio_domain.models import Desk

from facio_api.desk.database import get_db
from facio_api.desk.repository import DeskRepository

router = APIRouter(prefix="/v1/desk", tags=["desk"])

SessionDep = Annotated[AsyncSession, Depends(get_db)]


@router.get("/{account_id}")
async def get_desk(account_id: UUID, session: SessionDep) -> Desk:
    desk = await DeskRepository(session).load(account_id)
    if desk is None:
        raise HTTPException(status_code=404, detail="no desk stored for this account")
    return desk


@router.put("/{account_id}")
async def put_desk(account_id: UUID, desk: Desk, session: SessionDep) -> Desk:
    return await DeskRepository(session).merge_and_save(account_id, desk)
