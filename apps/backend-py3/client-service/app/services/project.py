from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Action, Project, ProjectStatus, StateVersion, User
from app.schemas.path import (
    ClarifyQuestion,
    ProjectDetail,
    StateVersionSummary,
)
from app.services.audit import AuditService
from app.services.serializers import (
    action_queue_key,
    serialize_action,
    serialize_groups,
)


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

    async def list_projects(self, user: User) -> list[Project]:
        result = await self.db.execute(
            select(Project)
            .where(
                Project.user_id == user.id,
                Project.status != ProjectStatus.abandoned,
            )
            .order_by(Project.updated_at.desc())
            .options(*self._project_options())
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
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found",
            )
        return project

    async def get_latest_state(self, project_id: UUID) -> tuple[int | None, dict]:
        result = await self.db.execute(
            select(StateVersion)
            .where(StateVersion.project_id == project_id)
            .order_by(StateVersion.version.desc())
            .limit(1)
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None, {}
        return row.version, row.state_json

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
                source=row.source.value
                if hasattr(row.source, "value")
                else str(row.source),
                created_at=row.created_at,
            )
            for row in rows
        ]

    async def to_detail(self, project: Project) -> ProjectDetail:
        version, state = await self.get_latest_state(project.id)
        questions = [
            ClarifyQuestion.model_validate(q)
            for q in state.get("questions", [])
        ]
        resources = list(state.get("resources", []) or [])
        ordered_actions = sorted(project.actions, key=action_queue_key)
        return ProjectDetail(
            id=project.id,
            status=project.status.value,
            raw_intent=project.raw_intent,
            outcome=project.outcome,
            paraphrase=project.paraphrase,
            success_criteria=project.success_criteria,
            horizon=project.horizon,
            committed_at=project.committed_at,
            created_at=project.created_at,
            updated_at=project.updated_at,
            groups=serialize_groups(project.groups),
            actions=[serialize_action(a) for a in ordered_actions],
            questions=questions,
            resources=resources,
            current_version=version,
        )

    async def commit(
        self,
        user: User,
        project_id: UUID,
        *,
        first_step_when: str | None = "today",
    ) -> Project:
        """Activate a draft project and stamp due_at on actions.

        next-action / execution queue uses group.sort then action.sort,
        not due_at. due_at is scheduling metadata from first_step_when +
        each action's day_offset (relative to the first queued action).
        """
        project = await self.get_project(user, project_id, for_update=True)
        if project.status != ProjectStatus.draft:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only draft projects can be committed",
            )
        if not project.actions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Project has no actions to commit",
            )
        if not project.outcome or not project.success_criteria:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Project contract incomplete",
            )

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
            event_type="project_committed",
            user_id=user.id,
            project_id=project.id,
            payload={"first_step_when": first_step_when},
        )
        await self.db.commit()
        await self.db.refresh(project)
        return await self.get_project(user, project.id)

    @staticmethod
    def _resolve_first_due(
        first_step_when: str | None, now: datetime
    ) -> datetime:
        value = (first_step_when or "today").strip().lower()
        if value == "tomorrow":
            return now + timedelta(days=1)
        return now
