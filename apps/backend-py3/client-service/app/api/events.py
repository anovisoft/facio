"""Client beacon / analytics events."""

from fastapi import APIRouter, HTTPException, status

from app.deps import CurrentUser, DbSession
from app.schemas.path import CreateEventRequest, EventResponse
from app.services.audit import CLIENT_EVENT_TYPES, AuditService
from app.services.project import ProjectService

router = APIRouter(prefix="/events", tags=["events"])


@router.post("", response_model=EventResponse, status_code=201)
async def create_event(
    body: CreateEventRequest,
    user: CurrentUser,
    db: DbSession,
) -> EventResponse:
    event_type = body.type.strip()
    if event_type not in CLIENT_EVENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Unknown event type '{event_type}'. "
                f"Allowed: {sorted(CLIENT_EVENT_TYPES)}"
            ),
        )

    if body.project_id is not None:
        await ProjectService(db).get_project(user, body.project_id)

    event = await AuditService(db).add_event(
        event_type=event_type,
        user_id=user.id,
        project_id=body.project_id,
        payload=body.payload or {},
    )
    await db.commit()
    await db.refresh(event)
    return EventResponse.model_validate(event, from_attributes=True)
