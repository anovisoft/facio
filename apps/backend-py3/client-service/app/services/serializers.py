from __future__ import annotations

from uuid import UUID

from app.models import Action, ActionGroup, ActionStatus, Project, ProjectStatus
from app.schemas.api import (
    ActionResponse,
    ChecklistItemResponse,
    GroupResponse,
)
from app.schemas.path_state import PathState
from app.services.path_materialize import action_key, stable_uuid


def serialize_action(action: Action) -> ActionResponse:
    group = action.group
    return ActionResponse(
        id=action.id,
        project_id=action.project_id,
        key=action.key,
        title=action.title,
        why=action.why,
        detail=action.detail,
        estimate_min=action.estimate_min,
        due_at=action.due_at,
        sort=action.sort,
        status=action.status.value,
        day_offset=action.day_offset,
        group_id=action.group_id,
        group_key=group.key if group else None,
        group_title=group.title if group else None,
        checklist_items=[
            ChecklistItemResponse.model_validate(item, from_attributes=True)
            for item in sorted(action.checklist_items, key=lambda i: i.sort)
        ],
    )


def serialize_groups(groups: list[ActionGroup]) -> list[GroupResponse]:
    return [
        GroupResponse.model_validate(g, from_attributes=True)
        for g in sorted(groups, key=lambda g: g.sort)
    ]


def serialize_path_state(
    project: Project, state: PathState
) -> tuple[list[GroupResponse], list[ActionResponse]]:
    """Serialize draft PathState into API shapes with stable uuid5 ids."""
    group_by_key = {g.id: g for g in state.groups}
    groups = [
        GroupResponse(
            id=stable_uuid(project.id, "group", g.id),
            key=g.id,
            title=g.title,
            description=g.description,
            sort=g.sort,
        )
        for g in sorted(state.groups, key=lambda g: g.sort)
    ]
    actions: list[ActionResponse] = []
    for index, item in enumerate(state.actions):
        key = action_key(item, index)
        action_id = stable_uuid(project.id, "action", key)
        group_key = item.group_id
        group_spec = group_by_key.get(group_key) if group_key else None
        sort = item.sort if item.sort is not None else index
        checklist = []
        for c_index, c in enumerate(item.checklist_items):
            c_key = c.id or f"c{c_index}"
            checklist.append(
                ChecklistItemResponse(
                    id=stable_uuid(project.id, "checklist", f"{key}:{c_key}"),
                    action_id=action_id,
                    key=c_key,
                    title=c.title,
                    done=c.done,
                    sort=c.sort if c.sort is not None else c_index,
                )
            )
        actions.append(
            ActionResponse(
                id=action_id,
                project_id=project.id,
                key=key,
                title=item.title,
                why=item.why,
                detail=item.detail,
                estimate_min=item.estimate_min,
                due_at=None,
                sort=sort,
                status=ActionStatus.pending.value,
                day_offset=item.day_offset,
                group_id=(
                    stable_uuid(project.id, "group", group_key)
                    if group_key
                    else None
                ),
                group_key=group_key,
                group_title=group_spec.title if group_spec else None,
                checklist_items=checklist,
            )
        )
    actions.sort(key=lambda a: (
        next((g.sort for g in groups if g.key == a.group_key), 10**9),
        a.sort,
    ))
    return groups, actions


def action_queue_key(action: Action) -> tuple[int, int]:
    """Order: group.sort (ungrouped last), then action.sort."""
    group_sort = action.group.sort if action.group is not None else 10**9
    return (group_sort, action.sort)


def pick_next_action(project: Project) -> Action | None:
    """First pending action for an active project (queue order)."""
    if project.status != ProjectStatus.active:
        return None
    pending = [a for a in project.actions if a.status == ActionStatus.pending]
    if not pending:
        return None
    return sorted(pending, key=action_queue_key)[0]
