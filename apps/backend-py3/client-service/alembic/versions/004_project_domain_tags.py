"""Add project domain/tags + domain metrics view.

Revision ID: 004
Revises: 003
Create Date: 2026-07-29
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "projects",
        sa.Column("domain", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "projects",
        sa.Column(
            "tags",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )
    op.create_index("ix_projects_domain", "projects", ["domain"])

    op.execute(
        """
        CREATE OR REPLACE VIEW mvp_domain_counts AS
        SELECT
            coalesce(domain, 'other') AS domain,
            count(*)::bigint AS projects,
            count(*) FILTER (
                WHERE status = 'active'
            )::bigint AS active_projects,
            count(*) FILTER (
                WHERE status = 'completed'
            )::bigint AS completed_projects,
            count(*) FILTER (
                WHERE committed_at IS NOT NULL
            )::bigint AS committed_projects
        FROM projects
        WHERE status != 'abandoned'
        GROUP BY coalesce(domain, 'other')
        """
    )


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS mvp_domain_counts")
    op.drop_index("ix_projects_domain", table_name="projects")
    op.drop_column("projects", "tags")
    op.drop_column("projects", "domain")
