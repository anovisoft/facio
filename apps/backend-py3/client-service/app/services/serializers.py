from __future__ import annotations

from app.models import Action
from app.schemas.path import (
    ActionResponse,
    ChecklistItemResponse,
    GroupResponse,
)


def serialize_action(action: Action) -> ActionResponse:
    group = action.group
    return ActionResponse(
        id=action.id,
        project_id=action.project_id,
        title=action.title,
        why=action.why,
        detail=action.detail,
        estimate_min=action.estimate_min,
        due_at=action.due_at,
        sort=action.sort,
        status=action.status.value
        if hasattr(action.status, "value")
        else str(action.status),
        day_offset=action.day_offset,
        group_id=action.group_id,
        group_key=group.key if group else None,
        group_title=group.title if group else None,
        checklist_items=[
            ChecklistItemResponse.model_validate(item, from_attributes=True)
            for item in sorted(action.checklist_items, key=lambda i: i.sort)
        ],
    )


def serialize_groups(groups) -> list[GroupResponse]:
    return [
        GroupResponse.model_validate(g, from_attributes=True)
        for g in sorted(groups, key=lambda g: g.sort)
    ]


def action_queue_key(action: Action) -> tuple[int, int]:
    """Order: group.sort (ungrouped last), then action.sort."""
    group_sort = action.group.sort if action.group is not None else 10**9
    return (group_sort, action.sort)
