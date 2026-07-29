"""Add day_offset and user_restore state source

Revision ID: 003
Revises: 002
Create Date: 2026-07-29

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "actions",
        sa.Column("day_offset", sa.Integer(), nullable=True),
    )
    # PostgreSQL: ADD VALUE is idempotent enough for MVP re-runs with IF NOT EXISTS
    # (PG 9.1+); use DO block for safety when value already present.
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_enum e
                JOIN pg_type t ON e.enumtypid = t.oid
                WHERE t.typname = 'state_source' AND e.enumlabel = 'user_restore'
            ) THEN
                ALTER TYPE state_source ADD VALUE 'user_restore';
            END IF;
        END$$;
        """
    )


def downgrade() -> None:
    op.drop_column("actions", "day_offset")
    # Enum value removal omitted (unsafe / unused in MVP).
