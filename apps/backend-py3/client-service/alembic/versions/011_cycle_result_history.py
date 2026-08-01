"""Add cycle_result + cycles_history for next-cycle (Slice 5).

Revision ID: 011
Revises: 010
Create Date: 2026-08-01
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "011"
down_revision: Union[str, None] = "010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "projects",
        sa.Column(
            "cycle_result",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )
    op.add_column(
        "projects",
        sa.Column(
            "cycles_history",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )
    # New state_versions.source for next-cycle Path snapshots.
    op.execute("ALTER TYPE state_source ADD VALUE IF NOT EXISTS 'llm_next_cycle'")


def downgrade() -> None:
    op.drop_column("projects", "cycles_history")
    op.drop_column("projects", "cycle_result")
    # Postgres cannot easily remove enum values; leave llm_next_cycle in place.
