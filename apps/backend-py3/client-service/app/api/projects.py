from uuid import UUID

from fastapi import APIRouter, Body, Query

from app.deps import CurrentUser, DbSession, LLM
from app.errors import AppError
from app.schemas.api import CreateIntentResponse
from app.schemas.path import (
    AbandonProjectRequest,
    ActionResponse,
    CommitProjectRequest,
    CreateProjectRequest,
    NextActionResponse,
    ProjectDetail,
    ProjectSummary,
    RefineProjectRequest,
    RepairProjectRequest,
    RestoreStateRequest,
)
from app.services.action import ActionService
from app.services.path import PathService
from app.services.project import ListStatusFilter, ProjectService
from app.services.serializers import serialize_action

router = APIRouter(prefix="/projects", tags=["projects"])


async def _commit_on_app_error(db: DbSession, exc: AppError) -> None:
    """Persist audit rows written before a domain failure, then re-raise."""
    await db.commit()
    raise exc


@router.get("", response_model=list[ProjectSummary])
async def list_projects(
    user: CurrentUser,
    db: DbSession,
    status: ListStatusFilter = Query(
        "open",
        description=(
            "open = non-abandoned (default Home); "
            "abandoned = archive only; "
            "or draft|active|completed"
        ),
    ),
) -> list[ProjectSummary]:
    service = ProjectService(db)
    projects = await service.list_projects(user, status=status)
    return [
        ProjectSummary.model_validate(p, from_attributes=True) for p in projects
    ]


@router.post("", response_model=CreateIntentResponse)
async def create_project(
    body: CreateProjectRequest,
    user: CurrentUser,
    db: DbSession,
    llm: LLM,
) -> CreateIntentResponse:
    service = PathService(db, llm=llm)
    try:
        return await service.create_from_intent(user, body.intent)
    except AppError as exc:
        await _commit_on_app_error(db, exc)


@router.get("/{project_id}", response_model=ProjectDetail)
async def get_project(
    project_id: UUID,
    user: CurrentUser,
    db: DbSession,
) -> ProjectDetail:
    service = ProjectService(db)
    project = await service.get_project(user, project_id)
    return await service.to_detail(project)


@router.get("/{project_id}/actions", response_model=list[ActionResponse])
async def list_actions(
    project_id: UUID,
    user: CurrentUser,
    db: DbSession,
) -> list[ActionResponse]:
    return await ProjectService(db).list_action_responses(user, project_id)


@router.get("/{project_id}/next-action", response_model=NextActionResponse)
async def next_action(
    project_id: UUID,
    user: CurrentUser,
    db: DbSession,
) -> NextActionResponse:
    action = await ActionService(db).get_next_action(user, project_id)
    return NextActionResponse(
        project_id=project_id,
        action=serialize_action(action) if action else None,
    )


@router.post("/{project_id}/refine", response_model=ProjectDetail)
async def refine_project(
    project_id: UUID,
    body: RefineProjectRequest,
    user: CurrentUser,
    db: DbSession,
    llm: LLM,
) -> ProjectDetail:
    service = PathService(db, llm=llm)
    try:
        project = await service.refine(
            user,
            project_id,
            answer=body.answer,
            question_id=body.question_id,
        )
    except AppError as exc:
        await _commit_on_app_error(db, exc)
    return await ProjectService(db).to_detail(project)


@router.post("/{project_id}/commit", response_model=ProjectDetail)
async def commit_project(
    project_id: UUID,
    body: CommitProjectRequest,
    user: CurrentUser,
    db: DbSession,
) -> ProjectDetail:
    service = ProjectService(db)
    project = await service.commit(
        user,
        project_id,
        first_step_when=body.first_step_when,
    )
    return await service.to_detail(project)


@router.post("/{project_id}/abandon", response_model=ProjectDetail)
async def abandon_project(
    project_id: UUID,
    user: CurrentUser,
    db: DbSession,
    body: AbandonProjectRequest = Body(default_factory=AbandonProjectRequest),
) -> ProjectDetail:
    service = ProjectService(db)
    project = await service.abandon(
        user,
        project_id,
        reason=body.reason,
    )
    return await service.to_detail(project)


@router.post("/{project_id}/restore-state", response_model=ProjectDetail)
async def restore_state(
    project_id: UUID,
    body: RestoreStateRequest,
    user: CurrentUser,
    db: DbSession,
) -> ProjectDetail:
    project = await PathService(db).restore_state(
        user, project_id, version=body.version
    )
    return await ProjectService(db).to_detail(project)


@router.post("/{project_id}/repair", response_model=ProjectDetail)
async def repair_project(
    project_id: UUID,
    body: RepairProjectRequest,
    user: CurrentUser,
    db: DbSession,
    llm: LLM,
) -> ProjectDetail:
    service = PathService(db, llm=llm)
    try:
        project = await service.repair(user, project_id, reason=body.reason)
    except AppError as exc:
        await _commit_on_app_error(db, exc)
    return await ProjectService(db).to_detail(project)
