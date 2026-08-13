"""Add cycle_anchor_date for the physical-day gate (Slice 4).

Revision ID: 009
Revises: 008
Create Date: 2026-07-31
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "projects",
        sa.Column("cycle_anchor_date", sa.Date(), nullable=True),
    )
    # Best-effort backfill for projects committed before this migration:
    # first_step_when isn't persisted, so approximate anchor as the commit
    # date (equivalent to first_step_when="today"). Slightly early is a much
    # smaller regression than leaving anchor NULL (which fully unlocks).
    op.execute(
        """
        UPDATE projects
        SET cycle_anchor_date = committed_at::date
        WHERE committed_at IS NOT NULL AND cycle_anchor_date IS NULL
        """
    )


def downgrade() -> None:
    op.drop_column("projects", "cycle_anchor_date")
