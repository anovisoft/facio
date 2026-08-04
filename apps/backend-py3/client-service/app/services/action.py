from __future__ import annotations

from copy import deepcopy
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import flag_modified

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
from app.services.cycle import build_cycle_result
from app.services.project import ProjectService
from app.services.schedule import parse_local_date
from app.services.schedule import unlocked_day_index as compute_unlocked_day_index
from app.services.serializers import action_queue_key

_COMMIT_REQUIRED = "Commit the project before executing steps"
_DAY_LOCKED = (
    "This day isn't open yet — it unlocks on the calendar date shown on "
    "the path."
)


class ActionService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.audit = AuditService(db)
        self.projects = ProjectService(db)

    @staticmethod
    def _require_active(project: Project) -> None:
        if project.status != ProjectStatus.active:
            raise ConflictError(_COMMIT_REQUIRED)

    @staticmethod
    def _require_unlocked(
        action: Action, project: Project, local_date: str | None
    ) -> None:
        """Physical-day gate (docs/next/04 §4): reject execute mutations on
        actions whose day is still in the future for the caller's calendar.
        Preview (read) is unaffected — this only guards write endpoints.
        """
        if action.day_offset is None:
            return
        unlocked = compute_unlocked_day_index(
            anchor=project.cycle_anchor_date,
            horizon_days=project.cycle_horizon_days or 1,
            local_today=parse_local_date(local_date),
        )
        if action.day_offset > unlocked:
            raise ConflictError(_DAY_LOCKED)

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
        # Full cycle finish: structured result + cycle_status for next-cycle CTA.
        result = build_cycle_result(project, partial=False)
        project.cycle_result = result.model_dump(mode="json")
        project.cycle_status = "completed"
        project.status = ProjectStatus.completed
        await self.audit.add_event(
            event_type=EventType.cycle_completed,
            user_id=user.id,
            project_id=project.id,
            payload={
                "cycle_index": project.cycle_index,
                "partial": False,
                "cycle_result": project.cycle_result,
            },
        )
        await self.audit.add_event(
            event_type=EventType.project_completed,
            user_id=user.id,
            project_id=project.id,
            payload={},
        )

    async def complete(
        self, user: User, action_id: UUID, *, local_date: str | None = None
    ) -> Action:
        action, project = await self._get_owned_action(user, action_id)
        self._require_active(project)
        if action.status != ActionStatus.pending:
            raise ConflictError(f"Action is already {action.status.value}")
        self._require_unlocked(action, project, local_date)

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

    async def skip(
        self, user: User, action_id: UUID, *, local_date: str | None = None
    ) -> Action:
        action, project = await self._get_owned_action(user, action_id)
        self._require_active(project)
        if action.status != ActionStatus.pending:
            raise ConflictError(f"Action is already {action.status.value}")
        self._require_unlocked(action, project, local_date)

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

    async def uncomplete(
        self, user: User, action_id: UUID, *, local_date: str | None = None
    ) -> Action:
        """Re-open a done/skipped Session as pending (Session chrome Back).

        Keeps checklist / counter / stepper / timer runtime. Physical-day
        gate still applies. Does not rewrite PathState.
        """
        action, project = await self._get_owned_action(user, action_id)
        self._require_active(project)
        if action.status not in {ActionStatus.done, ActionStatus.skipped}:
            raise ConflictError(
                f"Action is {action.status.value}; only done/skipped "
                "can be uncompleted"
            )
        self._require_unlocked(action, project, local_date)

        previous = action.status.value
        action.status = ActionStatus.pending
        await self.db.flush()

        await self.audit.add_event(
            event_type=EventType.action_uncompleted,
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
        local_date: str | None = None,
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
        self._require_unlocked(action, action.project, local_date)

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

    async def update_counter(
        self,
        user: User,
        action_id: UUID,
        *,
        current: int | None = None,
        delta: int | None = None,
        local_date: str | None = None,
    ) -> Action:
        action, project = await self._get_owned_action(user, action_id)
        self._require_active(project)
        if action.status != ActionStatus.pending:
            raise ConflictError("Cannot update counter on a closed action")
        self._require_unlocked(action, project, local_date)
        if not isinstance(action.counter, dict):
            raise ConflictError("Action has no counter")

        counter = deepcopy(action.counter)
        previous = int(counter.get("current") or 0)
        target = int(counter.get("target") or 0)
        if current is not None:
            new_current = current
        else:
            new_current = previous + int(delta or 0)
        new_current = max(0, new_current)
        if target > 0:
            new_current = min(new_current, target)
        counter["current"] = new_current
        action.counter = counter
        flag_modified(action, "counter")
        await self.db.flush()

        await self.audit.add_event(
            event_type=EventType.counter_updated,
            user_id=user.id,
            project_id=project.id,
            payload={
                "action_id": str(action.id),
                "previous_current": previous,
                "current": new_current,
                "target": target,
                "label": counter.get("label"),
            },
        )
        await self.db.commit()
        return (await self._get_owned_action(user, action_id))[0]

    async def update_stepper_beat_counter(
        self,
        user: User,
        action_id: UUID,
        beat_id: str,
        *,
        current: int | None = None,
        delta: int | None = None,
        local_date: str | None = None,
    ) -> Action:
        action, project = await self._get_owned_action(user, action_id)
        self._require_active(project)
        if action.status != ActionStatus.pending:
            raise ConflictError("Cannot update stepper on a closed action")
        self._require_unlocked(action, project, local_date)
        if not isinstance(action.stepper, dict):
            raise ConflictError("Action has no stepper")
        beats = action.stepper.get("beats")
        if not isinstance(beats, list) or not beats:
            raise ConflictError("Action has no stepper beats")

        stepper = deepcopy(action.stepper)
        updated_beats = stepper.get("beats") or []
        found = False
        previous = 0
        target = 0
        for beat in updated_beats:
            if not isinstance(beat, dict):
                continue
            if str(beat.get("id")) != beat_id:
                continue
            counter = beat.get("counter")
            if not isinstance(counter, dict):
                raise ConflictError("Stepper beat has no counter")
            previous = int(counter.get("current") or 0)
            target = int(counter.get("target") or 0)
            if current is not None:
                new_current = current
            else:
                new_current = previous + int(delta or 0)
            new_current = max(0, new_current)
            if target > 0:
                new_current = min(new_current, target)
            counter["current"] = new_current
            beat["counter"] = counter
            found = True
            break
        if not found:
            raise ConflictError("Stepper beat not found")

        stepper["beats"] = updated_beats
        action.stepper = stepper
        flag_modified(action, "stepper")
        await self.db.flush()

        await self.audit.add_event(
            event_type=EventType.counter_updated,
            user_id=user.id,
            project_id=project.id,
            payload={
                "action_id": str(action.id),
                "beat_id": beat_id,
                "previous_current": previous,
                "current": (
                    int(
                        next(
                            (
                                b["counter"]["current"]
                                for b in updated_beats
                                if isinstance(b, dict)
                                and str(b.get("id")) == beat_id
                            ),
                            0,
                        )
                    )
                ),
                "target": target,
                "plugin": "stepper",
            },
        )
        await self.db.commit()
        return (await self._get_owned_action(user, action_id))[0]

    async def complete_timer(
        self,
        user: User,
        action_id: UUID,
        timer_id: str,
        *,
        completed: bool = True,
        local_date: str | None = None,
    ) -> Action:
        action, project = await self._get_owned_action(user, action_id)
        self._require_active(project)
        if action.status != ActionStatus.pending:
            raise ConflictError("Cannot update timer on a closed action")
        self._require_unlocked(action, project, local_date)
        timers = action.timers if isinstance(action.timers, list) else []
        if not timers:
            raise ConflictError("Action has no timers")

        updated = deepcopy(timers)
        found = False
        previous = False
        for item in updated:
            if not isinstance(item, dict):
                continue
            if str(item.get("id")) != timer_id:
                continue
            found = True
            previous = bool(item.get("completed", False))
            item["completed"] = completed
            break
        if not found:
            raise NotFoundError("Timer not found")

        action.timers = updated
        flag_modified(action, "timers")
        await self.db.flush()

        await self.audit.add_event(
            event_type=EventType.timer_completed,
            user_id=user.id,
            project_id=project.id,
            payload={
                "action_id": str(action.id),
                "timer_id": timer_id,
                "previous_completed": previous,
                "completed": completed,
            },
        )
        await self.db.commit()
        return (await self._get_owned_action(user, action_id))[0]
