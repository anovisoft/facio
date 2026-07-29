from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PathAction(BaseModel):
    title: str = Field(min_length=1)
    why: str = Field(min_length=1)
    detail: str | None = None
    estimate_min: int | None = Field(default=None, ge=0)
    day_offset: int | None = Field(default=None, ge=0)


class ClarifyQuestion(BaseModel):
    id: str
    prompt: str
    options: list[str] = Field(default_factory=list)


class PathState(BaseModel):
    """Structured LLM output for create / refine / repair."""

    outcome: str = Field(min_length=1)
    paraphrase: str = Field(min_length=1)
    success_criteria: str = Field(min_length=1)
    horizon: str = Field(min_length=1)
    actions: list[PathAction] = Field(min_length=1)
    questions: list[ClarifyQuestion] = Field(default_factory=list)
    resources: list[str] = Field(default_factory=list)
    milestones: list[str] = Field(default_factory=list)

    @field_validator("actions")
    @classmethod
    def why_required(cls, actions: list[PathAction]) -> list[PathAction]:
        for action in actions:
            if not action.why.strip():
                raise ValueError("action.why must be non-empty")
        return actions


PATH_RESPONSE_SCHEMA: dict = PathState.model_json_schema()


class CreateProjectRequest(BaseModel):
    intent: str = Field(min_length=1, max_length=4000)


class RefineProjectRequest(BaseModel):
    answer: str = Field(min_length=1, max_length=4000)
    question_id: str | None = None


class RepairProjectRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=4000)


class CommitProjectRequest(BaseModel):
    first_step_when: str | None = Field(
        default="today",
        description="today | tomorrow | ISO date hint",
    )


class ActionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    title: str
    why: str
    detail: str | None
    estimate_min: int | None
    due_at: datetime | None
    sort: int
    status: str


class ProjectSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: str
    raw_intent: str
    outcome: str | None
    paraphrase: str | None
    success_criteria: str | None
    horizon: str | None
    committed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ProjectDetail(ProjectSummary):
    actions: list[ActionResponse] = Field(default_factory=list)
    questions: list[ClarifyQuestion] = Field(default_factory=list)
    resources: list[str] = Field(default_factory=list)
    current_version: int | None = None


class NextActionResponse(BaseModel):
    project_id: UUID
    action: ActionResponse | None


class ConversationTurnResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID | None
    role: str
    content: str
    meta: dict | None
    created_at: datetime


class TranscriptResponse(BaseModel):
    project_id: UUID
    turns: list[ConversationTurnResponse]
