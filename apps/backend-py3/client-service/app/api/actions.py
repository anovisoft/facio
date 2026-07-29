from uuid import UUID

from fastapi import APIRouter

from app.deps import CurrentUser, DbSession
from app.schemas.path import (
    ActionResponse,
    ChecklistItemResponse,
    ToggleChecklistItemRequest,
)
from app.services.action import ActionService
from app.services.serializers import serialize_action

router = APIRouter(tags=["actions"])


@router.post("/actions/{action_id}/complete", response_model=ActionResponse)
async def complete_action(
    action_id: UUID,
    user: CurrentUser,
    db: DbSession,
) -> ActionResponse:
    action = await ActionService(db).complete(user, action_id)
    return serialize_action(action)


@router.post("/actions/{action_id}/skip", response_model=ActionResponse)
async def skip_action(
    action_id: UUID,
    user: CurrentUser,
    db: DbSession,
) -> ActionResponse:
    action = await ActionService(db).skip(user, action_id)
    return serialize_action(action)


@router.post(
    "/checklist-items/{item_id}/toggle",
    response_model=ChecklistItemResponse,
)
async def toggle_checklist_item(
    item_id: UUID,
    user: CurrentUser,
    db: DbSession,
    body: ToggleChecklistItemRequest | None = None,
) -> ChecklistItemResponse:
    payload = body or ToggleChecklistItemRequest()
    item = await ActionService(db).toggle_checklist_item(
        user, item_id, done=payload.done
    )
    return ChecklistItemResponse.model_validate(item, from_attributes=True)
