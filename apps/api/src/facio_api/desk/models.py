"""One row per account: the whole desk, split into a structure JSON and a
progress JSON so the two can carry different conflict-resolution rules (Q20).
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import BigInteger, DateTime
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from facio_api.desk.database import Base


class DeskSnapshotRow(Base):
    __tablename__ = "desk_snapshots"

    account_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    structure: Mapped[dict] = mapped_column(JSONB, nullable=False)
    progress: Mapped[dict] = mapped_column(JSONB, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
