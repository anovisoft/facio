from uuid import UUID

from fastapi import APIRouter

from app.deps import CurrentUser, DbSession
from app.schemas.path import ActionResponse
from app.services.action import ActionService

router = APIRouter(prefix="/actions", tags=["actions"])


@router.post("/{action_id}/complete", response_model=ActionResponse)
async def complete_action(
    action_id: UUID,
    user: CurrentUser,
    db: DbSession,
) -> ActionResponse:
    action = await ActionService(db).complete(user, action_id)
    return ActionResponse.model_validate(action, from_attributes=True)


@router.post("/{action_id}/skip", response_model=ActionResponse)
async def skip_action(
    action_id: UUID,
    user: CurrentUser,
    db: DbSession,
) -> ActionResponse:
    action = await ActionService(db).skip(user, action_id)
    return ActionResponse.model_validate(action, from_attributes=True)
