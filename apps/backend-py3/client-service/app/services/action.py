from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    Action,
    ActionStatus,
    ChecklistItem,
    Project,
    ProjectStatus,
    User,
)
from app.services.audit import AuditService
from app.services.serializers import action_queue_key


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
            .options(
                selectinload(Action.project),
                selectinload(Action.group),
                selectinload(Action.checklist_items),
            )
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
            .options(
                selectinload(Action.group),
                selectinload(Action.checklist_items),
            )
        )
        actions = list(result.scalars().all())
        if not actions:
            return None
        return sorted(actions, key=action_queue_key)[0]

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
            .options(
                selectinload(Action.group),
                selectinload(Action.checklist_items),
            )
        )
        return sorted(list(result.scalars().all()), key=action_queue_key)

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

        incomplete = [i for i in action.checklist_items if not i.done]
        if incomplete:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Mark all checklist items before completing this action "
                    f"({len(incomplete)} remaining)"
                ),
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
        return (await self._get_owned_action(user, action_id))[0]

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
        return (await self._get_owned_action(user, action_id))[0]

    async def toggle_checklist_item(
        self,
        user: User,
        item_id: UUID,
        *,
        done: bool | None = None,
    ) -> ChecklistItem:
        result = await self.db.execute(
            select(ChecklistItem)
            .join(Action)
            .join(Project)
            .where(ChecklistItem.id == item_id, Project.user_id == user.id)
            .options(selectinload(ChecklistItem.action))
        )
        item = result.scalar_one_or_none()
        if item is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Checklist item not found",
            )

        action = item.action
        if action.status != ActionStatus.pending:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot toggle checklist on a closed action",
            )

        previous = item.done
        item.done = (not item.done) if done is None else done
        await self.db.flush()

        await self.audit.add_event(
            event_type="checklist_item_toggled",
            user_id=user.id,
            project_id=action.project_id,
            payload={
                "checklist_item_id": str(item.id),
                "action_id": str(action.id),
                "previous_done": previous,
                "done": item.done,
                "title": item.title,
            },
        )
        await self.db.commit()
        await self.db.refresh(item)
        return item
