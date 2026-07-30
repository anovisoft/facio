"""Apply PathState onto project ORM rows (commit / active repair)."""

from __future__ import annotations

from uuid import UUID, uuid5

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Action,
    ActionGroup,
    ActionStatus,
    ChecklistItem,
    Project,
)
from app.schemas.path_state import PathAction, PathState

# Stable draft/API ids derived from project + logical key.
PATH_ID_NAMESPACE = UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")


def action_key(item: PathAction, index: int) -> str:
    return item.id or f"a{index}"


def stable_uuid(project_id: UUID, kind: str, key: str) -> UUID:
    return uuid5(PATH_ID_NAMESPACE, f"{project_id}:{kind}:{key}")


def ensure_action_keys(state: PathState) -> PathState:
    """Return a copy of state with every action having a stable key in `id`."""
    actions: list[PathAction] = []
    for index, item in enumerate(state.actions):
        key = action_key(item, index)
        checklist = []
        for c_index, c in enumerate(item.checklist_items):
            checklist.append(
                c.model_copy(update={"id": c.id or f"c{c_index}"})
            )
        timers = []
        for t_index, timer in enumerate(item.timers):
            timers.append(
                timer.model_copy(update={"id": timer.id or f"t{t_index}"})
            )
        actions.append(
            item.model_copy(
                update={
                    "id": key,
                    "checklist_items": checklist,
                    "timers": timers,
                }
            )
        )
    return state.model_copy(update={"actions": actions})


def _timer_payload(
    timers: list,
    *,
    preserved_completed: dict[str, bool] | None = None,
) -> list[dict]:
    out: list[dict] = []
    done_map = preserved_completed or {}
    for t_index, timer in enumerate(timers):
        t_key = timer.id or f"t{t_index}"
        out.append(
            {
                "id": t_key,
                "title": timer.title,
                "duration_sec": timer.duration_sec,
                "signal": timer.signal,
                "parallel_group": timer.parallel_group,
                "completed": bool(done_map.get(t_key, False)),
            }
        )
    return out


def _counter_payload(
    counter,
    *,
    preserved_current: int | None = None,
) -> dict | None:
    if counter is None:
        return None
    current = (
        preserved_current if preserved_current is not None else counter.current
    )
    return {
        "label": counter.label,
        "target": counter.target,
        "current": max(0, int(current)),
        "step": counter.step if counter.step else 1,
    }


def apply_contract(project: Project, state: PathState) -> None:
    project.title = state.title
    project.summary = state.summary
    project.outcome = state.outcome
    project.paraphrase = state.paraphrase
    project.success_criteria = state.success_criteria
    project.horizon = state.horizon
    project.domain = state.domain
    project.tags = list(state.tags)
    project.cycle_index = state.cycle.index
    project.cycle_horizon_days = state.cycle.horizon_days
    project.cycle_status = state.cycle.status
    project.cycle_goal = state.cycle.goal_for_cycle
    project.schedule_days = [
        day.model_dump(mode="json") for day in state.days
    ]


async def materialize_path(
    db: AsyncSession,
    project: Project,
    state: PathState,
    *,
    merge_progress: bool = False,
) -> None:
    """Write groups/actions/checklists from PathState into ORM.

    merge_progress=True (active repair): keep status of done/skipped actions
    matched by key; rebuild the rest from state.
    """
    state = ensure_action_keys(state)
    apply_contract(project, state)

    preserved: dict[str, ActionStatus] = {}
    preserved_checklist: dict[str, dict[str, bool]] = {}
    preserved_counter: dict[str, int] = {}
    preserved_timers: dict[str, dict[str, bool]] = {}
    if merge_progress:
        for action in project.actions:
            if action.status in {ActionStatus.done, ActionStatus.skipped}:
                preserved[action.key] = action.status
                preserved_checklist[action.key] = {
                    (item.key or item.title): item.done
                    for item in action.checklist_items
                }
            if isinstance(action.counter, dict) and "current" in action.counter:
                preserved_counter[action.key] = int(action.counter["current"])
            if isinstance(action.timers, list):
                preserved_timers[action.key] = {
                    str(t.get("id")): bool(t.get("completed"))
                    for t in action.timers
                    if isinstance(t, dict) and t.get("id")
                }

    for action in list(project.actions):
        await db.delete(action)
    await db.flush()
    for group in list(project.groups):
        await db.delete(group)
    await db.flush()

    key_to_group: dict[str, ActionGroup] = {}
    for group_spec in sorted(state.groups, key=lambda g: g.sort):
        group = ActionGroup(
            project_id=project.id,
            key=group_spec.id,
            title=group_spec.title,
            description=group_spec.description,
            sort=group_spec.sort,
        )
        db.add(group)
        await db.flush()
        key_to_group[group_spec.id] = group

    for index, item in enumerate(state.actions):
        key = action_key(item, index)
        sort = item.sort if item.sort is not None else index
        group_uuid = None
        if item.group_id is not None:
            group_uuid = key_to_group[item.group_id].id
        status = preserved.get(key, ActionStatus.pending)
        action = Action(
            project_id=project.id,
            group_id=group_uuid,
            key=key,
            title=item.title,
            why=item.why,
            detail=item.detail,
            estimate_min=item.estimate_min,
            day_offset=item.day_offset,
            sort=sort,
            status=status,
            timers=_timer_payload(
                item.timers,
                preserved_completed=preserved_timers.get(key),
            ),
            counter=_counter_payload(
                item.counter,
                preserved_current=preserved_counter.get(key),
            ),
        )
        db.add(action)
        await db.flush()
        done_map = preserved_checklist.get(key, {})
        for c_index, checklist in enumerate(item.checklist_items):
            c_key = checklist.id or f"c{c_index}"
            done = done_map.get(c_key, checklist.done)
            if key in preserved and status == ActionStatus.done:
                done = done_map.get(c_key, True)
            db.add(
                ChecklistItem(
                    action_id=action.id,
                    key=c_key,
                    title=checklist.title,
                    done=done,
                    sort=checklist.sort if checklist.sort is not None else c_index,
                )
            )

    await db.flush()
    await db.refresh(project, attribute_names=["actions", "groups"])
