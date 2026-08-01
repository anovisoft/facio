from uuid import UUID

from fastapi import APIRouter, Query

from app.deps import CurrentUser, DbSession
from app.schemas.path import (
    ActionResponse,
    ChecklistItemResponse,
    CompleteTimerRequest,
    ToggleChecklistItemRequest,
    UpdateCounterRequest,
)
from app.services.action import ActionService
from app.services.serializers import serialize_action

router = APIRouter(tags=["actions"])

_LOCAL_DATE_DESC = (
    "Caller's local calendar date (YYYY-MM-DD), used for the physical-day "
    "unlock gate. Falls back to UTC today when omitted."
)


@router.post("/actions/{action_id}/complete", response_model=ActionResponse)
async def complete_action(
    action_id: UUID,
    user: CurrentUser,
    db: DbSession,
    local_date: str | None = Query(default=None, description=_LOCAL_DATE_DESC),
) -> ActionResponse:
    action = await ActionService(db).complete(
        user, action_id, local_date=local_date
    )
    return serialize_action(action)


@router.post("/actions/{action_id}/skip", response_model=ActionResponse)
async def skip_action(
    action_id: UUID,
    user: CurrentUser,
    db: DbSession,
    local_date: str | None = Query(default=None, description=_LOCAL_DATE_DESC),
) -> ActionResponse:
    action = await ActionService(db).skip(user, action_id, local_date=local_date)
    return serialize_action(action)


@router.post(
    "/checklist-items/{item_id}/toggle",
    response_model=ChecklistItemResponse,
)
async def toggle_checklist_item(
    item_id: UUID,
    body: ToggleChecklistItemRequest,
    user: CurrentUser,
    db: DbSession,
    local_date: str | None = Query(default=None, description=_LOCAL_DATE_DESC),
) -> ChecklistItemResponse:
    item = await ActionService(db).toggle_checklist_item(
        user, item_id, done=body.done, local_date=local_date
    )
    return ChecklistItemResponse.model_validate(item, from_attributes=True)


@router.post(
    "/actions/{action_id}/counter",
    response_model=ActionResponse,
)
async def update_counter(
    action_id: UUID,
    body: UpdateCounterRequest,
    user: CurrentUser,
    db: DbSession,
    local_date: str | None = Query(default=None, description=_LOCAL_DATE_DESC),
) -> ActionResponse:
    action = await ActionService(db).update_counter(
        user,
        action_id,
        current=body.current,
        delta=body.delta,
        local_date=local_date,
    )
    return serialize_action(action)


@router.post(
    "/actions/{action_id}/stepper/beats/{beat_id}/counter",
    response_model=ActionResponse,
)
async def update_stepper_beat_counter(
    action_id: UUID,
    beat_id: str,
    body: UpdateCounterRequest,
    user: CurrentUser,
    db: DbSession,
    local_date: str | None = Query(default=None, description=_LOCAL_DATE_DESC),
) -> ActionResponse:
    action = await ActionService(db).update_stepper_beat_counter(
        user,
        action_id,
        beat_id,
        current=body.current,
        delta=body.delta,
        local_date=local_date,
    )
    return serialize_action(action)


@router.post(
    "/actions/{action_id}/timers/{timer_id}/complete",
    response_model=ActionResponse,
)
async def complete_timer(
    action_id: UUID,
    timer_id: str,
    body: CompleteTimerRequest,
    user: CurrentUser,
    db: DbSession,
    local_date: str | None = Query(default=None, description=_LOCAL_DATE_DESC),
) -> ActionResponse:
    action = await ActionService(db).complete_timer(
        user,
        action_id,
        timer_id,
        completed=body.completed,
        local_date=local_date,
    )
    return serialize_action(action)
