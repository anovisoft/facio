"""Postgres views for MVP funnel / FCT KPIs (docs/mvp/04-metrics.md).

Revision ID: 003
Revises: 002
Create Date: 2026-07-29
"""

from typing import Sequence, Union

from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Raw counts by event type (sanity / Metabase starter).
    op.execute(
        """
        CREATE OR REPLACE VIEW mvp_event_counts AS
        SELECT
            type,
            count(*)::bigint AS events,
            count(DISTINCT user_id)::bigint AS users,
            count(DISTINCT project_id)::bigint AS projects
        FROM events
        GROUP BY type
        """
    )

    # Per-project timestamps for activation / FCT.
    op.execute(
        """
        CREATE OR REPLACE VIEW mvp_project_milestones AS
        SELECT
            p.id AS project_id,
            p.user_id,
            p.status,
            p.raw_intent,
            p.outcome,
            p.created_at AS project_created_at,
            p.committed_at,
            (
                SELECT min(e.created_at)
                FROM events e
                WHERE e.project_id = p.id AND e.type = 'intent_submitted'
            ) AS intent_at,
            (
                SELECT min(e.created_at)
                FROM events e
                WHERE e.project_id = p.id AND e.type = 'soft_start_shown'
            ) AS soft_start_at,
            (
                SELECT min(e.created_at)
                FROM events e
                WHERE e.project_id = p.id AND e.type = 'draft_shown'
            ) AS draft_at,
            (
                SELECT min(e.created_at)
                FROM events e
                WHERE e.project_id = p.id AND e.type = 'committed'
            ) AS committed_event_at,
            (
                SELECT min(e.created_at)
                FROM events e
                WHERE e.project_id = p.id AND e.type = 'first_completion'
            ) AS first_completion_at,
            (
                SELECT count(*)::bigint
                FROM events e
                WHERE e.project_id = p.id AND e.type = 'refine_answered'
            ) AS refine_count,
            (
                SELECT count(*)::bigint
                FROM events e
                WHERE e.project_id = p.id AND e.type = 'action_done'
            ) AS action_done_count,
            (
                SELECT count(*)::bigint
                FROM events e
                WHERE e.project_id = p.id AND e.type = 'path_opened'
            ) AS path_opened_count
        FROM projects p
        """
    )

    # FCT rows (only projects that reached first Сделано).
    op.execute(
        """
        CREATE OR REPLACE VIEW mvp_fct AS
        SELECT
            project_id,
            user_id,
            status,
            outcome,
            coalesce(intent_at, project_created_at) AS intent_at,
            coalesce(committed_event_at, committed_at) AS commit_at,
            first_completion_at,
            extract(
                epoch FROM (
                    first_completion_at
                    - coalesce(intent_at, project_created_at)
                )
            ) / 3600.0 AS fct_intent_hours,
            extract(
                epoch FROM (
                    first_completion_at
                    - coalesce(committed_event_at, committed_at)
                )
            ) / 3600.0 AS fct_commit_hours,
            (
                date_trunc('day', first_completion_at)
                = date_trunc(
                    'day',
                    coalesce(committed_event_at, committed_at)
                )
            ) AS same_day_first_completion
        FROM mvp_project_milestones
        WHERE first_completion_at IS NOT NULL
          AND coalesce(committed_event_at, committed_at) IS NOT NULL
        """
    )

    # Weekly-style activation snapshot (scalars as one row).
    op.execute(
        """
        CREATE OR REPLACE VIEW mvp_activation_kpis AS
        WITH base AS (
            SELECT
                (
                    SELECT count(*)::numeric
                    FROM events
                    WHERE type = 'intent_submitted'
                ) AS intent_submitted,
                (
                    SELECT count(*)::numeric
                    FROM events
                    WHERE type = 'instant_answer_shown'
                ) AS instant_answer_shown,
                (
                    SELECT count(*)::numeric
                    FROM events
                    WHERE type = 'draft_shown'
                ) AS draft_shown,
                (
                    SELECT count(*)::numeric
                    FROM events
                    WHERE type = 'soft_start_shown'
                ) AS soft_start_shown,
                (
                    SELECT count(*)::numeric
                    FROM events
                    WHERE type = 'committed'
                ) AS committed,
                (
                    SELECT count(DISTINCT project_id)::numeric
                    FROM events
                    WHERE type = 'refine_answered'
                ) AS projects_with_refine,
                (
                    SELECT count(*)::numeric
                    FROM mvp_fct
                    WHERE same_day_first_completion
                ) AS same_day_first_completions,
                (
                    SELECT count(*)::numeric FROM mvp_fct
                ) AS first_completions
        )
        SELECT
            intent_submitted,
            instant_answer_shown,
            soft_start_shown,
            draft_shown,
            committed,
            projects_with_refine,
            same_day_first_completions,
            first_completions,
            CASE
                WHEN intent_submitted > 0
                THEN committed / intent_submitted
            END AS commit_rate,
            CASE
                WHEN intent_submitted > 0
                THEN draft_shown / intent_submitted
            END AS draft_success_rate,
            CASE
                WHEN intent_submitted > 0
                THEN instant_answer_shown / intent_submitted
            END AS instant_answer_rate,
            CASE
                WHEN draft_shown > 0
                THEN projects_with_refine / draft_shown
            END AS refine_rate,
            CASE
                WHEN committed > 0
                THEN same_day_first_completions / committed
            END AS same_day_first_completion_rate
        FROM base
        """
    )

    # Multi-active share + path revisit helpers.
    op.execute(
        """
        CREATE OR REPLACE VIEW mvp_user_project_stats AS
        SELECT
            u.id AS user_id,
            u.device_id,
            u.created_at AS user_created_at,
            count(*) FILTER (
                WHERE p.status = 'active'
            )::bigint AS active_projects,
            count(*) FILTER (
                WHERE p.status = 'draft'
            )::bigint AS draft_projects,
            count(*) FILTER (
                WHERE p.status = 'completed'
            )::bigint AS completed_projects,
            count(*) FILTER (
                WHERE p.committed_at IS NOT NULL
            )::bigint AS committed_projects,
            bool_or(
                EXISTS (
                    SELECT 1
                    FROM events e
                    WHERE e.project_id = p.id AND e.type = 'path_opened'
                )
            ) AS any_path_opened
        FROM users u
        LEFT JOIN projects p ON p.user_id = u.id
        GROUP BY u.id, u.device_id, u.created_at
        """
    )

    # Audit completeness: create/refine calls missing raw or unpaired state.
    op.execute(
        """
        CREATE OR REPLACE VIEW mvp_audit_gaps AS
        SELECT
            c.id AS llm_call_id,
            c.project_id,
            c.user_id,
            c.purpose,
            c.parsed_ok,
            c.created_at,
            (c.raw_response IS NULL) AS missing_raw_response,
            (
                c.parsed_ok
                AND c.project_id IS NOT NULL
                AND NOT EXISTS (
                    SELECT 1
                    FROM state_versions sv
                    WHERE sv.project_id = c.project_id
                      AND sv.created_at >= c.created_at - interval '2 seconds'
                      AND sv.created_at <= c.created_at + interval '2 seconds'
                )
            ) AS missing_nearby_state_version
        FROM llm_calls c
        WHERE c.purpose IN ('create', 'refine', 'repair')
        """
    )


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS mvp_audit_gaps")
    op.execute("DROP VIEW IF EXISTS mvp_user_project_stats")
    op.execute("DROP VIEW IF EXISTS mvp_activation_kpis")
    op.execute("DROP VIEW IF EXISTS mvp_fct")
    op.execute("DROP VIEW IF EXISTS mvp_project_milestones")
    op.execute("DROP VIEW IF EXISTS mvp_event_counts")
