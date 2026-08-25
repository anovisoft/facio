"""Async SQLAlchemy engine/session. One engine per database URL, cached."""

from __future__ import annotations

from collections.abc import AsyncIterator
from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from facio_api.config import Settings, get_settings


class Base(DeclarativeBase):
    pass


@lru_cache
def _engine(database_url: str) -> AsyncEngine:
    return create_async_engine(database_url, pool_pre_ping=True)


@lru_cache
def _sessionmaker(database_url: str) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(_engine(database_url), expire_on_commit=False)


SettingsDep = Annotated[Settings, Depends(get_settings)]


async def get_db(settings: SettingsDep) -> AsyncIterator[AsyncSession]:
    session_factory = _sessionmaker(settings.database_url)
    async with session_factory() as session:
        yield session
