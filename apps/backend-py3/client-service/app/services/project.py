from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.errors import ConflictError, NotFoundError, ValidationAppError
from app.models import Action, ConversationTurn, Project, ProjectStatus, StateVersion, User
from app.schemas.api import (
    ActionResponse,
    ProjectDetail,
    ProjectSummary,
    StateVersionSummary,
)
from app.schemas.path_state import PathState
from app.services.audit import AuditService, EventType
from app.services.path_materialize import (
    ensure_action_keys,
    materialize_path,
    path_plugins_ready,
)
from app.services.schedule import (
    day_unlock_date,
    is_day_locked,
    parse_local_date,
    resolve_cycle_anchor,
    unlocked_day_index as compute_unlocked_day_index,
)
from app.services.serializers import (
    action_queue_key,
    pick_focus_action,
    pick_next_action,
    resolve_current_day,
    serialize_action,
    serialize_cycle_from_project,
    serialize_cycle_from_state,
    serialize_days_from_project,
    serialize_days_from_state,
    serialize_groups,
    serialize_path_state,
)

ListStatusFilter = Literal[
    "open", "abandoned", "draft", "active", "completed"
]

logger = logging.getLogger(__name__)


class ProjectService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.audit = AuditService(db)

    def _project_options(self):
        return (
            selectinload(Project.groups),
            selectinload(Project.actions).selectinload(Action.group),
            selectinload(Project.actions).selectinload(Action.checklist_items),
        )

    async def list_projects(
        self,
        user: User,
        *,
        status: ListStatusFilter = "open",
    ) -> list[Project]:
        """List projects. Default ``open`` = everything except abandoned."""
        stmt = select(Project).where(Project.user_id == user.id)
        if status == "open":
            stmt = stmt.where(Project.status != ProjectStatus.abandoned)
        else:
            stmt = stmt.where(Project.status == ProjectStatus(status))

        result = await self.db.execute(
            stmt.order_by(Project.updated_at.desc()).options(
                *self._project_options()
            )
        )
        return list(result.scalars().all())

    async def get_project(
        self, user: User, project_id: UUID, *, for_update: bool = False
    ) -> Project:
        stmt = (
            select(Project)
            .where(Project.id == project_id, Project.user_id == user.id)
            .options(*self._project_options())
        )
        if for_update:
            stmt = stmt.with_for_update()
        result = await self.db.execute(stmt)
        project = result.scalar_one_or_none()
        if project is None:
            raise NotFoundError("Project not found")
        return project

    async def abandon(
        self,
        user: User,
        project_id: UUID,
        *,
        reason: str | None = None,
    ) -> Project:
        project = await self.get_project(user, project_id, for_update=True)
        if project.status == ProjectStatus.abandoned:
            raise ConflictError("Project is already abandoned")
        if project.status == ProjectStatus.completed:
            raise ConflictError("Completed projects cannot be abandoned")

        previous = project.status.value
        project.status = ProjectStatus.abandoned
        await self.audit.add_event(
            event_type=EventType.project_abandoned,
            user_id=user.id,
            project_id=project.id,
            payload={
                "previous_status": previous,
                "reason": reason,
            },
        )
        await self.db.commit()
        return await self.get_project(user, project.id)

    async def get_latest_state(
        self, project_id: UUID, *, strict: bool = False
    ) -> tuple[int | None, PathState | None]:
        """Load latest PathState.

        On validation failure: when ``strict`` is False (reads / Home),
        return ``(version, None)`` so callers can fall back to ORM and
        never surface raw pydantic dumps to the client. When ``strict``
        is True (commit / writes that need a valid state), raise a short
        ValidationAppError.
        """
        result = await self.db.execute(
            select(StateVersion)
            .where(StateVersion.project_id == project_id)
            .order_by(StateVersion.version.desc())
            .limit(1)
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None, None
        try:
            return row.version, PathState.model_validate(row.state_json)
        except ValidationError as exc:
            logger.warning(
                "Invalid PathState project=%s version=%s: %s",
                project_id,
                row.version,
                exc,
            )
            if strict:
                raise ValidationAppError(
                    "Latest path state could not be loaded"
                ) from exc
            return row.version, None

    async def list_state_versions(
        self, user: User, project_id: UUID
    ) -> list[StateVersionSummary]:
        await self.get_project(user, project_id)
        result = await self.db.execute(
            select(StateVersion)
            .where(StateVersion.project_id == project_id)
            .order_by(StateVersion.version.asc())
        )
        rows = list(result.scalars().all())
        return [
            StateVersionSummary(
                version=row.version,
                source=row.source.value,
                created_at=row.created_at,
            )
            for row in rows
        ]

    async def list_action_responses(
        self, user: User, project_id: UUID
    ) -> list[ActionResponse]:
        project = await self.get_project(user, project_id)
        if project.status == ProjectStatus.draft:
            _, state = await self.get_latest_state(project.id)
            if state is None:
                return []
            _, actions = serialize_path_state(project, state)
            return actions
        ordered = sorted(project.actions, key=action_queue_key)
        return [serialize_action(a) for a in ordered]

    def to_summary(
        self, project: Project, *, local_date: str | None = None
    ) -> ProjectSummary:
        cycle = serialize_cycle_from_project(project)
        days = serialize_days_from_project(project)

        unlocked: int | None = None
        next_action: ActionResponse | None = None
        peek_action: ActionResponse | None = None
        next_unlock_date = None
        if project.status == ProjectStatus.active:
            local_today = parse_local_date(local_date)
            unlocked = compute_unlocked_day_index(
                anchor=project.cycle_anchor_date,
                horizon_days=project.cycle_horizon_days or 1,
                local_today=local_today,
            )
            focus_orm = pick_focus_action(project, unlocked)
            if focus_orm is not None:
                next_action = serialize_action(focus_orm, day_locked=False)
            else:
                peek_orm = pick_next_action(project)
                if peek_orm is not None:
                    peek_action = serialize_action(peek_orm, day_locked=True)
                    next_unlock_date = day_unlock_date(
                        project.cycle_anchor_date, peek_orm.day_offset
                    )

        current_day = resolve_current_day(
            cycle=cycle,
            days=days,
            next_action=next_action,
            unlocked_day_index=unlocked,
        )
        peek_day = (
            resolve_current_day(
                cycle=cycle,
                days=days,
                next_action=peek_action,
                unlocked_day_index=unlocked,
            )
            if peek_action is not None
            else None
        )
        return ProjectSummary.model_validate(
            project, from_attributes=True
        ).model_copy(
            update={
                "next_action": next_action,
                "cycle": cycle,
                "current_day": current_day,
                "unlocked_day_index": unlocked,
                "cycle_anchor_date": project.cycle_anchor_date,
                "peek_action": peek_action,
                "peek_day": peek_day,
                "next_unlock_date": next_unlock_date,
            }
        )

    async def to_detail(
        self, project: Project, *, local_date: str | None = None
    ) -> ProjectDetail:
        version, state = await self.get_latest_state(project.id)
        questions = list(state.questions) if state else []
        resources = list(state.resources) if state else []
        milestones = list(state.milestones) if state else []

        if project.status == ProjectStatus.draft and state is not None:
            groups, actions = serialize_path_state(project, state)
            cycle = serialize_cycle_from_state(state)
            days = serialize_days_from_state(state)
        else:
            ordered_actions = sorted(project.actions, key=action_queue_key)
            groups = serialize_groups(project.groups)
            actions = [serialize_action(a) for a in ordered_actions]
            cycle = serialize_cycle_from_project(project)
            days = serialize_days_from_project(project)
            if cycle is None and state is not None:
                cycle = serialize_cycle_from_state(state)
            if not days and state is not None:
                days = serialize_days_from_state(state)
            # Overlay plugin_hints from PathState (ORM has no hints column).
            if state is not None:
                hints_by_key = {
                    (a.id or f"a{i}"): list(a.plugin_hints or [])
                    for i, a in enumerate(state.actions)
                }
                actions = [
                    a.model_copy(
                        update={"plugin_hints": hints_by_key.get(a.key or "", [])}
                    )
                    for a in actions
                ]

        unlocked: int | None = None
        next_action: ActionResponse | None = None
        peek_action: ActionResponse | None = None
        next_unlock_date = None
        if project.status == ProjectStatus.active:
            local_today = parse_local_date(local_date)
            unlocked = compute_unlocked_day_index(
                anchor=project.cycle_anchor_date,
                horizon_days=project.cycle_horizon_days or 1,
                local_today=local_today,
            )
            # Preview locked days (must, docs/next/04 §4): future days stay
            # visible on Path / «Весь план»; only mark them non-executable.
            actions = [
                a.model_copy(
                    update={"day_locked": is_day_locked(a.day_offset, unlocked)}
                )
                for a in actions
            ]
            focus_orm = pick_focus_action(project, unlocked)
            if focus_orm is not None:
                next_action = serialize_action(focus_orm, day_locked=False)
                if state is not None:
                    for i, sa in enumerate(state.actions):
                        key = sa.id or f"a{i}"
                        if key == next_action.key:
                            next_action = next_action.model_copy(
                                update={"plugin_hints": list(sa.plugin_hints or [])}
                            )
                            break
            else:
                peek_orm = pick_next_action(project)
                if peek_orm is not None:
                    peek_action = serialize_action(peek_orm, day_locked=True)
                    next_unlock_date = day_unlock_date(
                        project.cycle_anchor_date, peek_orm.day_offset
                    )

        current_day = resolve_current_day(
            cycle=cycle,
            days=days,
            next_action=next_action,
            unlocked_day_index=unlocked,
        )
        peek_day = (
            resolve_current_day(
                cycle=cycle,
                days=days,
                next_action=peek_action,
                unlocked_day_index=unlocked,
            )
            if peek_action is not None
            else None
        )

        path_ready = (
            bool(actions) if project.status == ProjectStatus.draft else True
        )
        path_error = None
        if project.status == ProjectStatus.draft and not path_ready:
            path_error = await self._latest_turn_meta_error(
                project.id, kind="path_error"
            )

        plugins_ready = True
        if state is not None:
            plugins_ready = path_plugins_ready(state)
            # Active project waiting on #3: state may still lack payloads.
            if (
                project.status == ProjectStatus.active
                and not plugins_ready
            ):
                plugins_ready = False
        elif project.status == ProjectStatus.active:
            # Degraded read: invalid PathState — ORM is source of truth;
            # don't lock Home on an infinite plugins spinner.
            plugins_ready = True

        plugins_error = None
        if project.status == ProjectStatus.active and not plugins_ready:
            plugins_error = await self._latest_plugins_error(project.id)

        summary = ProjectSummary.model_validate(
            project, from_attributes=True
        ).model_copy(
            update={
                "next_action": next_action,
                "cycle": cycle,
                "current_day": current_day,
                "unlocked_day_index": unlocked,
                "cycle_anchor_date": project.cycle_anchor_date,
                "peek_action": peek_action,
                "peek_day": peek_day,
                "next_unlock_date": next_unlock_date,
            }
        )
        return ProjectDetail(
            **summary.model_dump(),
            groups=groups,
            days=days,
            actions=actions,
            questions=questions,
            resources=resources,
            milestones=milestones,
            current_version=version,
            path_ready=path_ready,
            path_error=path_error,
            plugins_ready=plugins_ready,
            plugins_error=plugins_error,
        )

    async def _latest_turn_meta_error(
        self, project_id: UUID, *, kind: str
    ) -> str | None:
        result = await self.db.execute(
            select(ConversationTurn)
            .where(
                ConversationTurn.project_id == project_id,
            )
            .order_by(ConversationTurn.created_at.desc())
            .limit(20)
        )
        for turn in result.scalars().all():
            meta = turn.meta or {}
            if meta.get("kind") == kind:
                err = meta.get("error")
                return str(err) if err else turn.content
        return None

    async def _latest_plugins_error(self, project_id: UUID) -> str | None:
        """Return plugins_error only if it's the newest plugins-related turn.

        A later ``plugins_retrying`` or ``plugins_ready`` clears the sticky
        error so Home can show the loader again after retry.
        """
        result = await self.db.execute(
            select(ConversationTurn)
            .where(
                ConversationTurn.project_id == project_id,
            )
            .order_by(ConversationTurn.created_at.desc())
            .limit(20)
        )
        for turn in result.scalars().all():
            meta = turn.meta or {}
            kind = meta.get("kind")
            if kind in ("plugins_ready", "plugins_retrying"):
                return None
            if kind == "plugins_error":
                err = meta.get("error")
                return str(err) if err else turn.content
        return None

    async def _latest_path_error(self, project_id: UUID) -> str | None:
        return await self._latest_turn_meta_error(
            project_id, kind="path_error"
        )

    async def commit(
        self,
        user: User,
        project_id: UUID,
        *,
        first_step_when: Literal["today", "tomorrow"] = "today",
    ) -> Project:
        """Materialize PathState into ORM and activate the project."""
        project = await self.get_project(user, project_id, for_update=True)
        if project.status != ProjectStatus.draft:
            raise ConflictError("Only draft projects can be committed")

        version, state = await self.get_latest_state(project.id, strict=True)
        if state is None:
            raise ValidationAppError("Project has no Path state to commit")
        if not state.actions:
            raise ValidationAppError("Path is still generating — try again shortly")
        if not state.outcome or not state.success_criteria:
            raise ValidationAppError("Project contract incomplete")

        state = ensure_action_keys(state)
        # Accept activates the current cycle.
        state = state.model_copy(
            update={
                "cycle": state.cycle.model_copy(update={"status": "active"}),
            }
        )
        await materialize_path(self.db, project, state, merge_progress=False)

        if not project.actions:
            raise ValidationAppError("Project has no actions to commit")

        now = datetime.now(UTC)
        project.status = ProjectStatus.active
        project.committed_at = now
        project.cycle_status = "active"
        project.cycle_anchor_date = resolve_cycle_anchor(
            committed_at=now, first_step_when=first_step_when
        )

        ordered = sorted(project.actions, key=action_queue_key)
        base = self._resolve_first_due(first_step_when, now)
        first_offset = (
            ordered[0].day_offset
            if ordered[0].day_offset is not None
            else 0
        )
        for action in ordered:
            offset = (
                action.day_offset
                if action.day_offset is not None
                else action.sort
            )
            action.due_at = base + timedelta(
                days=max(0, offset - first_offset)
            )

        await self.audit.add_event(
            event_type=EventType.committed,
            user_id=user.id,
            project_id=project.id,
            payload={
                "first_step_when": first_step_when,
                "version": version,
            },
        )
        await self.db.commit()
        return await self.get_project(user, project.id)

    @staticmethod
    def _resolve_first_due(
        first_step_when: Literal["today", "tomorrow"], now: datetime
    ) -> datetime:
        if first_step_when == "tomorrow":
            return now + timedelta(days=1)
        return now
