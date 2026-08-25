"""desk_snapshots

Revision ID: 001
Revises:
Create Date: 2026-08-25

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "desk_snapshots",
        sa.Column("account_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("structure", postgresql.JSONB(), nullable=False),
        sa.Column("progress", postgresql.JSONB(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("desk_snapshots")
