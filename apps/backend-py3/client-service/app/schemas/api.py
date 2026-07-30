from datetime import datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Discriminator, Field, Tag, field_validator

from app.schemas.path_state import ClarifyQuestion, PathState


class CreateProjectRequest(BaseModel):
    intent: str = Field(min_length=1, max_length=4000)


class RefineProjectRequest(BaseModel):
    answer: str = Field(min_length=1, max_length=4000)
    question_id: str | None = None


class RepairProjectRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=4000)


class CommitProjectRequest(BaseModel):
    first_step_when: Literal["today", "tomorrow"] = "today"


class RestoreStateRequest(BaseModel):
    version: int = Field(ge=1)


class CreateEventRequest(BaseModel):
    type: str = Field(min_length=1, max_length=100)
    project_id: UUID | None = None
    payload: dict = Field(default_factory=dict)


class EventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    type: str
    user_id: UUID | None
    project_id: UUID | None
    payload: dict | None
    created_at: datetime


class StateVersionSummary(BaseModel):
    version: int
    source: str
    created_at: datetime


class ToggleChecklistItemRequest(BaseModel):
    done: bool | None = Field(
        default=None,
        description="If omitted, flips current done state",
    )


class ChecklistItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    action_id: UUID
    key: str | None = None
    title: str
    done: bool
    sort: int


class GroupResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    key: str
    title: str
    sort: int


class ActionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    key: str | None = None
    title: str
    why: str
    detail: str | None
    estimate_min: int | None
    due_at: datetime | None
    sort: int
    status: str
    day_offset: int | None = None
    group_id: UUID | None = None
    group_key: str | None = None
    group_title: str | None = None
    checklist_items: list[ChecklistItemResponse] = Field(default_factory=list)


class ProjectSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: str
    raw_intent: str
    outcome: str | None
    paraphrase: str | None
    success_criteria: str | None
    horizon: str | None
    domain: str | None = None
    tags: list[str] = Field(default_factory=list)
    committed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    next_action: ActionResponse | None = Field(
        default=None,
        description=(
            "Current «Сегодня» step for active projects; null for draft / "
            "completed / abandoned or when no pending actions remain."
        ),
    )

    @field_validator("tags", mode="before")
    @classmethod
    def empty_tags(cls, value: list[str] | None) -> list[str]:
        return list(value or [])


class ProjectDetail(ProjectSummary):
    groups: list[GroupResponse] = Field(default_factory=list)
    actions: list[ActionResponse] = Field(default_factory=list)
    questions: list[ClarifyQuestion] = Field(default_factory=list)
    resources: list[str] = Field(default_factory=list)
    milestones: list[str] = Field(default_factory=list)
    current_version: int | None = None


class AbandonProjectRequest(BaseModel):
    reason: str | None = Field(
        default=None,
        max_length=2000,
        description="Optional note for audit (why the path was abandoned).",
    )


class InstantAnswerResponse(BaseModel):
    kind: Literal["instant_answer"] = "instant_answer"
    label: str
    answer: str
    goal_suggestions: list[str]
    raw_intent: str
    llm_call_id: UUID
    event_id: UUID | None = None
    domain: str | None = None


class PathCreatedResponse(BaseModel):
    kind: Literal["path"] = "path"
    project: ProjectDetail


CreateIntentResponse = Annotated[
    Annotated[InstantAnswerResponse, Tag("instant_answer")]
    | Annotated[PathCreatedResponse, Tag("path")],
    Discriminator("kind"),
]


class ConversationTurnResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID | None
    role: str
    content: str
    meta: dict | None
    created_at: datetime
    state: PathState | None = None


class TranscriptResponse(BaseModel):
    project_id: UUID
    turns: list[ConversationTurnResponse]


class TimelineEntry(BaseModel):
    at: datetime
    kind: str
    turn: ConversationTurnResponse | None = None
    state_version: int | None = None
    state: PathState | None = None
    llm_call_id: UUID | None = None
    event_type: str | None = None
    event_payload: dict[str, Any] | None = None


class TimelineResponse(BaseModel):
    project_id: UUID
    entries: list[TimelineEntry]
