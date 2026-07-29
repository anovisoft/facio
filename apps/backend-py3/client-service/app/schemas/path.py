from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PathChecklistItem(BaseModel):
    id: str | None = None
    title: str = Field(min_length=1)
    done: bool = False
    sort: int = Field(default=0, ge=0)


class PathGroup(BaseModel):
    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    sort: int = Field(default=0, ge=0)


class PathAction(BaseModel):
    id: str | None = None
    title: str = Field(min_length=1)
    why: str = Field(min_length=1)
    detail: str | None = None
    estimate_min: int | None = Field(default=None, ge=0)
    day_offset: int | None = Field(default=None, ge=0)
    sort: int | None = Field(default=None, ge=0)
    group_id: str | None = None
    checklist_items: list[PathChecklistItem] = Field(default_factory=list)


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
    groups: list[PathGroup] = Field(default_factory=list)
    actions: list[PathAction] = Field(min_length=1)
    questions: list[ClarifyQuestion] = Field(default_factory=list)
    resources: list[str] = Field(default_factory=list)
    milestones: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_path(self) -> "PathState":
        group_ids = {g.id for g in self.groups}
        if len(group_ids) != len(self.groups):
            raise ValueError("groups[].id must be unique")

        for action in self.actions:
            if not action.why.strip():
                raise ValueError("action.why must be non-empty")
            if action.group_id is not None and action.group_id not in group_ids:
                raise ValueError(
                    f"action.group_id '{action.group_id}' has no matching group"
                )
            for item in action.checklist_items:
                if not item.title.strip():
                    raise ValueError("checklist_items.title must be non-empty")
        return self


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
    title: str
    why: str
    detail: str | None
    estimate_min: int | None
    due_at: datetime | None
    sort: int
    status: str
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
    committed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ProjectDetail(ProjectSummary):
    groups: list[GroupResponse] = Field(default_factory=list)
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
