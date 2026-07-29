from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Action, ActionStatus, Project, ProjectStatus, User
from app.services.audit import AuditService


class ActionService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.audit = AuditService(db)

    async def _get_owned_action(
        self, user: User, action_id: UUID
    ) -> tuple[Action, Project]:
        result = await self.db.execute(
            select(Action)
            .join(Project)
            .where(Action.id == action_id, Project.user_id == user.id)
            .options(selectinload(Action.project))
        )
        action = result.scalar_one_or_none()
        if action is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Action not found",
            )
        return action, action.project

    async def get_next_action(
        self, user: User, project_id: UUID
    ) -> Action | None:
        result = await self.db.execute(
            select(Project).where(
                Project.id == project_id, Project.user_id == user.id
            )
        )
        project = result.scalar_one_or_none()
        if project is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found",
            )

        result = await self.db.execute(
            select(Action)
            .where(
                Action.project_id == project_id,
                Action.status == ActionStatus.pending,
            )
            .order_by(Action.sort.asc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def list_actions(self, user: User, project_id: UUID) -> list[Action]:
        result = await self.db.execute(
            select(Project).where(
                Project.id == project_id, Project.user_id == user.id
            )
        )
        if result.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found",
            )

        result = await self.db.execute(
            select(Action)
            .where(Action.project_id == project_id)
            .order_by(Action.sort.asc())
        )
        return list(result.scalars().all())

    async def complete(self, user: User, action_id: UUID) -> Action:
        action, project = await self._get_owned_action(user, action_id)
        if project.status not in {ProjectStatus.active, ProjectStatus.draft}:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Project is not executable",
            )
        if action.status != ActionStatus.pending:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Action is already {action.status.value}",
            )

        previous = action.status.value
        action.status = ActionStatus.done
        await self.db.flush()

        await self.audit.add_event(
            event_type="action_completed",
            user_id=user.id,
            project_id=project.id,
            payload={
                "action_id": str(action.id),
                "previous_status": previous,
                "new_status": action.status.value,
            },
        )

        pending = await self.db.execute(
            select(Action).where(
                Action.project_id == project.id,
                Action.status == ActionStatus.pending,
            )
        )
        remaining = list(pending.scalars().all())
        if not remaining and project.status == ProjectStatus.active:
            project.status = ProjectStatus.completed
            await self.audit.add_event(
                event_type="project_completed",
                user_id=user.id,
                project_id=project.id,
                payload={},
            )

        done_count_result = await self.db.execute(
            select(func.count())
            .select_from(Action)
            .where(
                Action.project_id == project.id,
                Action.status == ActionStatus.done,
            )
        )
        if done_count_result.scalar_one() == 1:
            await self.audit.add_event(
                event_type="first_completion",
                user_id=user.id,
                project_id=project.id,
                payload={"action_id": str(action.id)},
            )

        await self.db.commit()
        await self.db.refresh(action)
        return action

    async def skip(self, user: User, action_id: UUID) -> Action:
        action, project = await self._get_owned_action(user, action_id)
        if project.status not in {ProjectStatus.active, ProjectStatus.draft}:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Project is not executable",
            )
        if action.status != ActionStatus.pending:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Action is already {action.status.value}",
            )

        previous = action.status.value
        action.status = ActionStatus.skipped
        await self.audit.add_event(
            event_type="action_skipped",
            user_id=user.id,
            project_id=project.id,
            payload={
                "action_id": str(action.id),
                "previous_status": previous,
                "new_status": action.status.value,
            },
        )
        await self.db.commit()
        await self.db.refresh(action)
        return action
