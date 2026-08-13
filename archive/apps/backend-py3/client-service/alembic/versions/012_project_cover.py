"""Add Guide Cover fields on projects (Facio 0.1 Slice B).

Revision ID: 012
Revises: 011
Create Date: 2026-08-03
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "012"
down_revision: Union[str, None] = "011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "projects",
        sa.Column("cover_emoji", sa.String(length=16), nullable=True),
    )
    op.add_column(
        "projects",
        sa.Column("cover_difficulty", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "projects",
        sa.Column(
            "cover_duration_summary", sa.String(length=64), nullable=True
        ),
    )


def downgrade() -> None:
    op.drop_column("projects", "cover_duration_summary")
    op.drop_column("projects", "cover_difficulty")
    op.drop_column("projects", "cover_emoji")
