from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Body, Query

from app.deps import CurrentUser, DbSession, LLM
from app.errors import AppError
from app.schemas.api import CreateIntentResponse
from app.schemas.path import (
    AbandonProjectRequest,
    ActionResponse,
    CommitProjectRequest,
    CreateProjectRequest,
    ProjectDetail,
    ProjectSummary,
    RefineProjectRequest,
    RepairProjectRequest,
    RestoreStateRequest,
    StateVersionSummary,
)
from app.services.path import (
    PathService,
    complete_create_path_job,
    complete_materialize_plugins_job,
)
from app.services.project import ListStatusFilter, ProjectService

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
    return [service.to_summary(p) for p in projects]


@router.post("", response_model=CreateIntentResponse)
async def create_project(
    body: CreateProjectRequest,
    user: CurrentUser,
    db: DbSession,
    llm: LLM,
    background_tasks: BackgroundTasks,
) -> CreateIntentResponse:
    service = PathService(db, llm=llm)
    try:
        result, pending = await service.create_from_intent(user, body.intent)
    except AppError as exc:
        await _commit_on_app_error(db, exc)
    if pending is not None:
        background_tasks.add_task(
            complete_create_path_job,
            project_id=pending.project_id,
            user_id=pending.user_id,
            intent=pending.intent,
            path_start=pending.path_start.model_dump(mode="json"),
            gate_llm_call_id=pending.gate_llm_call_id,
        )
    return result


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


@router.get(
    "/{project_id}/state-versions",
    response_model=list[StateVersionSummary],
)
async def list_state_versions(
    project_id: UUID,
    user: CurrentUser,
    db: DbSession,
) -> list[StateVersionSummary]:
    """Draft undo targets for «Назад» (append-only log; filter on client)."""
    return await ProjectService(db).list_state_versions(user, project_id)


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
            answers=[
                {"question_id": item.question_id, "value": item.value}
                for item in body.answers
            ],
            comment=body.comment,
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
    llm: LLM,
    background_tasks: BackgroundTasks,
) -> ProjectDetail:
    service = ProjectService(db)
    project = await service.commit(
        user,
        project_id,
        first_step_when=body.first_step_when,
    )
    detail = await service.to_detail(project)
    # Phase-3: materialize plugins in background when hints still unfilled.
    path_service = PathService(db, llm=llm)
    if await path_service.needs_plugin_materialize(user, project.id):
        background_tasks.add_task(
            complete_materialize_plugins_job,
            project_id=project.id,
            user_id=user.id,
        )
    return detail


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
