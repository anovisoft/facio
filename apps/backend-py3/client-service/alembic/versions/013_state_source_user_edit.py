"""Add state_source.user_edit for deterministic path edits (postpone).

Revision ID: 013
Revises: 012
Create Date: 2026-08-04
"""

from typing import Sequence, Union

from alembic import op

revision: str = "013"
down_revision: Union[str, None] = "012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE state_source ADD VALUE IF NOT EXISTS 'user_edit'")


def downgrade() -> None:
    # Postgres cannot easily remove enum values; leave user_edit in place.
    pass
