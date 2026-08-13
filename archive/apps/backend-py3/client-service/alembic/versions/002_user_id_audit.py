"""Add user_id to conversation_turns and llm_calls for instant_answer chronology.

Revision ID: 002
Revises: 001
Create Date: 2026-07-29
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "conversation_turns",
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_conversation_turns_user_id", "conversation_turns", ["user_id"]
    )

    op.add_column(
        "llm_calls",
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_llm_calls_user_id", "llm_calls", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_llm_calls_user_id", table_name="llm_calls")
    op.drop_column("llm_calls", "user_id")
    op.drop_index(
        "ix_conversation_turns_user_id", table_name="conversation_turns"
    )
    op.drop_column("conversation_turns", "user_id")
