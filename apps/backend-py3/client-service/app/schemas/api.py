from datetime import datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Discriminator,
    Field,
    Tag,
    field_validator,
    model_validator,
)

from app.schemas.path_state import (
    ClarifyQuestion,
    DayKind,
    PathState,
    TimerSignal,
)


class CreateProjectRequest(BaseModel):
    intent: str = Field(min_length=1, max_length=4000)


class RefineAnswerItem(BaseModel):
    question_id: str = Field(min_length=1, max_length=100)
    value: str = Field(min_length=1, max_length=2000)


class RefineProjectRequest(BaseModel):
    """Batch clarify: answers for the round + optional free-text comment.

    Legacy single ``answer`` / ``question_id`` still accepted and normalized
    into ``answers`` so older clients keep working.
    """

    answers: list[RefineAnswerItem] = Field(default_factory=list)
    comment: str | None = Field(default=None, max_length=4000)
    answer: str | None = Field(
        default=None,
        min_length=1,
        max_length=4000,
        description="Deprecated: single answer; prefer answers[].",
    )
    question_id: str | None = Field(
        default=None,
        description="Deprecated: pairs with legacy answer.",
    )

    @model_validator(mode="after")
    def normalize_and_require_payload(self) -> "RefineProjectRequest":
        answers = list(self.answers)
        if self.answer is not None:
            answers.append(
                RefineAnswerItem(
                    question_id=self.question_id or "_free",
                    value=self.answer,
                )
            )
        comment = (self.comment or "").strip() or None
        if not answers and not comment:
            raise ValueError(
                "Provide answers[] and/or comment (or legacy answer)"
            )
        return self.model_copy(
            update={"answers": answers, "comment": comment}
        )


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


class UpdateCounterRequest(BaseModel):
    """Set counter.current absolutely, or delta relative to current."""

    current: int | None = Field(default=None, ge=0)
    delta: int | None = Field(default=None)

    @model_validator(mode="after")
    def require_one(self) -> "UpdateCounterRequest":
        if self.current is None and self.delta is None:
            raise ValueError("Provide current and/or delta")
        return self


class CompleteTimerRequest(BaseModel):
    completed: bool = True


class ChecklistItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    action_id: UUID
    key: str | None = None
    title: str
    done: bool
    sort: int


class TimerResponse(BaseModel):
    id: str
    title: str
    duration_sec: int
    signal: TimerSignal
    parallel_group: str | None = None
    completed: bool = False


class CounterResponse(BaseModel):
    label: str | None = None
    target: int
    current: int
    step: int = 1


class TimelineMarkerResponse(BaseModel):
    at_sec: int
    title: str
    signal: TimerSignal


class ActionTimelineResponse(BaseModel):
    """Session axis + markers (cook). Named to avoid audit TimelineResponse."""

    duration_sec: int
    markers: list[TimelineMarkerResponse] = Field(default_factory=list)


class IntervalSegmentResponse(BaseModel):
    duration_sec: int
    title: str
    signal: TimerSignal = "nudge"


class IntervalPlanResponse(BaseModel):
    segments: list[IntervalSegmentResponse] = Field(default_factory=list)


class GroupResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    key: str
    title: str
    description: str | None = None
    sort: int


class CycleResponse(BaseModel):
    index: int
    horizon_days: int
    status: str
    goal_for_cycle: str | None = None


class DayResponse(BaseModel):
    day_index: int
    kind: DayKind
    title: str | None = None
    summary: str | None = None


class CurrentDayResponse(BaseModel):
    """«Сегодня» framing: day N of M with kind (1-based day_number for UI)."""

    day_index: int
    day_number: int
    horizon_days: int
    kind: DayKind
    title: str | None = None
    summary: str | None = None


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
    timers: list[TimerResponse] = Field(default_factory=list)
    counter: CounterResponse | None = None
    timeline: ActionTimelineResponse | None = None
    interval_plan: IntervalPlanResponse | None = None


class ProjectSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: str
    raw_intent: str
    title: str | None = None
    summary: str | None = None
    outcome: str | None
    paraphrase: str | None
    success_criteria: str | None
    horizon: str | None
    domain: str | None = None
    tags: list[str] = Field(default_factory=list)
    cycle: CycleResponse | None = None
    current_day: CurrentDayResponse | None = None
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
    days: list[DayResponse] = Field(default_factory=list)
    actions: list[ActionResponse] = Field(default_factory=list)
    questions: list[ClarifyQuestion] = Field(default_factory=list)
    resources: list[str] = Field(default_factory=list)
    milestones: list[str] = Field(default_factory=list)
    current_version: int | None = None
    path_ready: bool = Field(
        default=True,
        description=(
            "False while progressive create phase-2 Path+plugins is still "
            "generating (start surface already available)."
        ),
    )


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
