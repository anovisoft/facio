"""Add cycle + schedule days on projects.

Revision ID: 006
Revises: 005
Create Date: 2026-07-30
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "projects",
        sa.Column("cycle_index", sa.Integer(), nullable=True),
    )
    op.add_column(
        "projects",
        sa.Column("cycle_horizon_days", sa.Integer(), nullable=True),
    )
    op.add_column(
        "projects",
        sa.Column("cycle_status", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "projects",
        sa.Column("cycle_goal", sa.Text(), nullable=True),
    )
    op.add_column(
        "projects",
        sa.Column(
            "schedule_days",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("projects", "schedule_days")
    op.drop_column("projects", "cycle_goal")
    op.drop_column("projects", "cycle_status")
    op.drop_column("projects", "cycle_horizon_days")
    op.drop_column("projects", "cycle_index")
