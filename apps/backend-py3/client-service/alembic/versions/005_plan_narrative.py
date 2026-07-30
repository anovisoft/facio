"""Add plan narrative title/summary + group description.

Revision ID: 005
Revises: 004
Create Date: 2026-07-30
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "projects",
        sa.Column("title", sa.String(length=120), nullable=True),
    )
    op.add_column(
        "projects",
        sa.Column("summary", sa.Text(), nullable=True),
    )
    op.add_column(
        "action_groups",
        sa.Column("description", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("action_groups", "description")
    op.drop_column("projects", "summary")
    op.drop_column("projects", "title")
