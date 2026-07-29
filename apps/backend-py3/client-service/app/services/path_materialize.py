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
        actions.append(
            item.model_copy(update={"id": key, "checklist_items": checklist})
        )
    return state.model_copy(update={"actions": actions})


def apply_contract(project: Project, state: PathState) -> None:
    project.outcome = state.outcome
    project.paraphrase = state.paraphrase
    project.success_criteria = state.success_criteria
    project.horizon = state.horizon


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
    if merge_progress:
        for action in project.actions:
            if action.status in {ActionStatus.done, ActionStatus.skipped}:
                preserved[action.key] = action.status
                preserved_checklist[action.key] = {
                    (item.key or item.title): item.done
                    for item in action.checklist_items
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
