from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from facio_api.accounts.models import AccountRow


class AccountRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_or_create_by_apple_sub(
        self, apple_sub: str, *, email: str | None
    ) -> AccountRow:
        existing = await self._session.scalar(
            select(AccountRow).where(AccountRow.apple_sub == apple_sub)
        )
        if existing is not None:
            return existing
        row = AccountRow(
            id=uuid.uuid4(),
            apple_sub=apple_sub,
            email=email,
            created_at=datetime.now(timezone.utc),
        )
        self._session.add(row)
        await self._session.commit()
        return row
