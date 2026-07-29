"""Add path groups and checklist items

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
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "action_groups" not in tables:
        op.create_table(
            "action_groups",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "project_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("projects.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("key", sa.String(100), nullable=False),
            sa.Column("title", sa.String(255), nullable=False),
            sa.Column("sort", sa.Integer(), nullable=False, server_default="0"),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.UniqueConstraint(
                "project_id", "key", name="uq_action_groups_project_key"
            ),
        )
        op.create_index(
            "ix_action_groups_project_id", "action_groups", ["project_id"]
        )

    action_cols = {c["name"] for c in inspector.get_columns("actions")}
    if "group_id" not in action_cols:
        op.add_column(
            "actions",
            sa.Column(
                "group_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("action_groups.id", ondelete="SET NULL"),
                nullable=True,
            ),
        )
        op.create_index("ix_actions_group_id", "actions", ["group_id"])

    if "checklist_items" not in tables:
        op.create_table(
            "checklist_items",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "action_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("actions.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("key", sa.String(100), nullable=True),
            sa.Column("title", sa.String(500), nullable=False),
            sa.Column(
                "done",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            ),
            sa.Column("sort", sa.Integer(), nullable=False, server_default="0"),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
        )
        op.create_index(
            "ix_checklist_items_action_id", "checklist_items", ["action_id"]
        )


def downgrade() -> None:
    op.drop_table("checklist_items")
    op.drop_index("ix_actions_group_id", table_name="actions")
    op.drop_column("actions", "group_id")
    op.drop_table("action_groups")
