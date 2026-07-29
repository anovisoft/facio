from uuid import UUID

from fastapi import APIRouter

from app.deps import CurrentUser, DbSession, LLM
from app.schemas.path import (
    ActionResponse,
    CommitProjectRequest,
    ConversationTurnResponse,
    CreateProjectRequest,
    NextActionResponse,
    ProjectDetail,
    ProjectSummary,
    RefineProjectRequest,
    RepairProjectRequest,
    TranscriptResponse,
)
from app.services.action import ActionService
from app.services.path import PathService
from app.services.project import ProjectService

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=list[ProjectSummary])
async def list_projects(user: CurrentUser, db: DbSession) -> list[ProjectSummary]:
    service = ProjectService(db)
    projects = await service.list_projects(user)
    return [
        ProjectSummary.model_validate(p, from_attributes=True) for p in projects
    ]


@router.post("", response_model=ProjectDetail, status_code=201)
async def create_project(
    body: CreateProjectRequest,
    user: CurrentUser,
    db: DbSession,
    llm: LLM,
) -> ProjectDetail:
    service = PathService(db, llm=llm)
    project = await service.create_from_intent(user, body.intent)
    return await ProjectService(db).to_detail(project)


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
    actions = await ActionService(db).list_actions(user, project_id)
    return [
        ActionResponse.model_validate(a, from_attributes=True) for a in actions
    ]


@router.get("/{project_id}/next-action", response_model=NextActionResponse)
async def next_action(
    project_id: UUID,
    user: CurrentUser,
    db: DbSession,
) -> NextActionResponse:
    action = await ActionService(db).get_next_action(user, project_id)
    return NextActionResponse(
        project_id=project_id,
        action=(
            ActionResponse.model_validate(action, from_attributes=True)
            if action
            else None
        ),
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
    project = await service.refine(
        user,
        project_id,
        answer=body.answer,
        question_id=body.question_id,
    )
    return await ProjectService(db).to_detail(project)


@router.post("/{project_id}/commit", response_model=ProjectDetail)
async def commit_project(
    project_id: UUID,
    user: CurrentUser,
    db: DbSession,
    body: CommitProjectRequest | None = None,
) -> ProjectDetail:
    payload = body or CommitProjectRequest()
    service = ProjectService(db)
    project = await service.commit(
        user,
        project_id,
        first_step_when=payload.first_step_when,
    )
    return await service.to_detail(project)


@router.post("/{project_id}/repair", response_model=ProjectDetail)
async def repair_project(
    project_id: UUID,
    body: RepairProjectRequest,
    user: CurrentUser,
    db: DbSession,
    llm: LLM,
) -> ProjectDetail:
    service = PathService(db, llm=llm)
    project = await service.repair(user, project_id, reason=body.reason)
    return await ProjectService(db).to_detail(project)


@router.get("/{project_id}/transcript", response_model=TranscriptResponse)
async def get_transcript(
    project_id: UUID,
    user: CurrentUser,
    db: DbSession,
) -> TranscriptResponse:
    turns = await PathService(db).get_transcript(user, project_id)
    return TranscriptResponse(
        project_id=project_id,
        turns=[
            ConversationTurnResponse.model_validate(t, from_attributes=True)
            for t in turns
        ],
    )
