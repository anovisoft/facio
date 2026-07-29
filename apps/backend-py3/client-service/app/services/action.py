from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.errors import ConflictError, NotFoundError
from app.models import (
    Action,
    ActionStatus,
    ChecklistItem,
    Project,
    ProjectStatus,
    User,
)
from app.services.audit import AuditService, EventType
from app.services.project import ProjectService
from app.services.serializers import action_queue_key

_COMMIT_REQUIRED = "Commit the project before executing steps"


class ActionService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.audit = AuditService(db)
        self.projects = ProjectService(db)

    @staticmethod
    def _require_active(project: Project) -> None:
        if project.status != ProjectStatus.active:
            raise ConflictError(_COMMIT_REQUIRED)

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
            raise NotFoundError("Action not found")
        return action, action.project

    async def get_next_action(
        self, user: User, project_id: UUID
    ) -> Action | None:
        await self.projects.get_project(user, project_id)
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
        project = await self.projects.get_project(user, project_id)
        result = await self.db.execute(
            select(Action)
            .where(Action.project_id == project.id)
            .options(
                selectinload(Action.group),
                selectinload(Action.checklist_items),
            )
        )
        return sorted(list(result.scalars().all()), key=action_queue_key)

    async def _complete_project_if_no_pending(
        self, user: User, project: Project
    ) -> None:
        pending = await self.db.execute(
            select(Action).where(
                Action.project_id == project.id,
                Action.status == ActionStatus.pending,
            )
        )
        if pending.scalars().first() is not None:
            return
        project.status = ProjectStatus.completed
        await self.audit.add_event(
            event_type=EventType.project_completed,
            user_id=user.id,
            project_id=project.id,
            payload={},
        )

    async def complete(self, user: User, action_id: UUID) -> Action:
        action, project = await self._get_owned_action(user, action_id)
        self._require_active(project)
        if action.status != ActionStatus.pending:
            raise ConflictError(f"Action is already {action.status.value}")

        incomplete = [i for i in action.checklist_items if not i.done]
        if incomplete:
            raise ConflictError(
                "Mark all checklist items before completing this action "
                f"({len(incomplete)} remaining)"
            )

        previous = action.status.value
        action.status = ActionStatus.done
        await self.db.flush()

        await self.audit.add_event(
            event_type=EventType.action_done,
            user_id=user.id,
            project_id=project.id,
            payload={
                "action_id": str(action.id),
                "previous_status": previous,
                "new_status": action.status.value,
            },
        )

        await self._complete_project_if_no_pending(user, project)

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
                event_type=EventType.first_completion,
                user_id=user.id,
                project_id=project.id,
                payload={"action_id": str(action.id)},
            )

        await self.db.commit()
        return (await self._get_owned_action(user, action_id))[0]

    async def skip(self, user: User, action_id: UUID) -> Action:
        action, project = await self._get_owned_action(user, action_id)
        self._require_active(project)
        if action.status != ActionStatus.pending:
            raise ConflictError(f"Action is already {action.status.value}")

        previous = action.status.value
        action.status = ActionStatus.skipped
        await self.db.flush()

        await self.audit.add_event(
            event_type=EventType.action_skipped,
            user_id=user.id,
            project_id=project.id,
            payload={
                "action_id": str(action.id),
                "previous_status": previous,
                "new_status": action.status.value,
            },
        )
        await self._complete_project_if_no_pending(user, project)
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
            .options(
                selectinload(ChecklistItem.action).selectinload(Action.project),
            )
        )
        item = result.scalar_one_or_none()
        if item is None:
            raise NotFoundError("Checklist item not found")

        action = item.action
        self._require_active(action.project)
        if action.status != ActionStatus.pending:
            raise ConflictError("Cannot toggle checklist on a closed action")

        previous = item.done
        item.done = (not item.done) if done is None else done
        await self.db.flush()

        await self.audit.add_event(
            event_type=EventType.checklist_item_toggled,
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
