from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.errors import ConflictError, NotFoundError, ValidationAppError
from app.models import Action, Project, ProjectStatus, StateVersion, User
from app.schemas.api import (
    ActionResponse,
    ProjectDetail,
    ProjectSummary,
    StateVersionSummary,
)
from app.schemas.path_state import PathState
from app.services.audit import AuditService, EventType
from app.services.path_materialize import ensure_action_keys, materialize_path
from app.services.serializers import (
    action_queue_key,
    pick_next_action,
    serialize_action,
    serialize_groups,
    serialize_path_state,
)

ListStatusFilter = Literal[
    "open", "abandoned", "draft", "active", "completed"
]


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
        self, project_id: UUID
    ) -> tuple[int | None, PathState | None]:
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
            raise ValidationAppError(
                f"Latest state version is invalid: {exc}"
            ) from exc

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

    def to_summary(self, project: Project) -> ProjectSummary:
        next_orm = pick_next_action(project)
        return ProjectSummary.model_validate(
            project, from_attributes=True
        ).model_copy(
            update={
                "next_action": (
                    serialize_action(next_orm) if next_orm else None
                ),
            }
        )

    async def to_detail(self, project: Project) -> ProjectDetail:
        version, state = await self.get_latest_state(project.id)
        questions = list(state.questions) if state else []
        resources = list(state.resources) if state else []
        milestones = list(state.milestones) if state else []

        if project.status == ProjectStatus.draft and state is not None:
            groups, actions = serialize_path_state(project, state)
        else:
            ordered_actions = sorted(project.actions, key=action_queue_key)
            groups = serialize_groups(project.groups)
            actions = [serialize_action(a) for a in ordered_actions]

        summary = self.to_summary(project)
        return ProjectDetail(
            **summary.model_dump(),
            groups=groups,
            actions=actions,
            questions=questions,
            resources=resources,
            milestones=milestones,
            current_version=version,
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

        version, state = await self.get_latest_state(project.id)
        if state is None:
            raise ValidationAppError("Project has no Path state to commit")
        if not state.outcome or not state.success_criteria:
            raise ValidationAppError("Project contract incomplete")

        state = ensure_action_keys(state)
        await materialize_path(self.db, project, state, merge_progress=False)

        if not project.actions:
            raise ValidationAppError("Project has no actions to commit")

        now = datetime.now(UTC)
        project.status = ProjectStatus.active
        project.committed_at = now

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
