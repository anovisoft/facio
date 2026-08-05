from datetime import date, datetime
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


RepairIntent = Literal["shift", "lighten", "rest"]

ContinueKind = Literal["next", "repeat"]


class CycleResultResponse(BaseModel):
    """Structured cycle summary for Home / next-cycle prompt (docs/next/04 §7)."""

    completed_steps: int = 0
    skipped_steps: int = 0
    pending_steps: int = 0
    partial: bool = False
    partial_notes: str | None = None
    counters_snapshot: list[dict[str, Any]] = Field(default_factory=list)
    user_comment: str | None = None
    finished_at: datetime | None = None


class CycleHistoryEntry(BaseModel):
    """Lean archived cycle so the user can see «what was» (cycle 1…)."""

    index: int
    horizon_days: int
    goal_for_cycle: str | None = None
    title: str | None = None
    summary: str | None = None
    cycle_result: CycleResultResponse | None = None
    path_snapshot: dict[str, Any] | None = Field(
        default=None,
        description="Lean prior Path (title/summary/days/actions titles).",
    )
    completed_at: datetime | None = None


class CompleteCycleRequest(BaseModel):
    """Explicit «Завершить цикл» with optional partial notes / comment."""

    partial_notes: str | None = Field(default=None, max_length=4000)
    user_comment: str | None = Field(default=None, max_length=4000)


class NextCycleRequest(BaseModel):
    """Start cycle N+1 (or cook «Повторить») with optional clarify batch."""

    answers: list[RefineAnswerItem] = Field(default_factory=list)
    comment: str | None = Field(default=None, max_length=4000)

    @model_validator(mode="after")
    def normalize_comment(self) -> "NextCycleRequest":
        comment = (self.comment or "").strip() or None
        return self.model_copy(update={"comment": comment})


class RepairDiffLine(BaseModel):
    """One human-readable before → after row for Repair confirm."""

    before: str
    after: str


class RepairPreviewResponse(BaseModel):
    """Dry-run Repair: Diff + proposed PathState, nothing persisted."""

    before_version: int = Field(
        description="Current state_version; pass back on confirm apply.",
    )
    summary: str | None = Field(
        default=None,
        description="Repair-flavored paraphrase for the Diff header.",
    )
    diff: list[RepairDiffLine] = Field(default_factory=list)
    proposed_state: dict[str, Any] = Field(
        description="Validated PathState JSON to send on POST .../repair apply.",
    )


class RepairProjectRequest(BaseModel):
    """Structured «Не могу» gesture: pick an intent and/or free reason.

    Two-phase (Facio 0.1 Slice E): preview first, then apply with
    ``proposed_state`` + ``before_version``. One-shot (intent/reason only)
    still runs LLM + commit for back-compat / scripts.
    """

    intent: RepairIntent | None = None
    reason: str | None = Field(default=None, max_length=4000)
    proposed_state: dict[str, Any] | None = Field(
        default=None,
        description="From POST .../repair/preview — apply without re-running LLM.",
    )
    before_version: int | None = Field(
        default=None,
        ge=1,
        description="Required with proposed_state; rejects if Guide moved.",
    )

    @model_validator(mode="after")
    def require_one(self) -> "RepairProjectRequest":
        if self.proposed_state is not None:
            if self.before_version is None:
                raise ValueError(
                    "before_version is required when applying proposed_state"
                )
            return self
        if self.intent is None and not (self.reason or "").strip():
            raise ValueError("Provide intent and/or reason")
        return self

class CommitProjectRequest(BaseModel):
    first_step_when: Literal["today", "tomorrow"] = "today"


class RestoreStateRequest(BaseModel):
    version: int = Field(ge=1)


class PathStateSnapshotResponse(BaseModel):
    """Current PathState JSON + version for Manual editor (Slice E2b)."""

    version: int = Field(ge=1)
    state: dict[str, Any] = Field(
        description="Validated PathState JSON (actions include tool payloads).",
    )


class ManualEditRequest(BaseModel):
    """Deterministic Manual editor apply — no LLM (Facio 0.1 Slice E2b).

    Client fetches PathState via GET .../path-state, mutates closed UI Block
    tool fields, then posts the full proposed_state with before_version.
    """

    before_version: int = Field(
        ge=1,
        description="Current state_version; rejects if Guide moved.",
    )
    proposed_state: dict[str, Any] = Field(
        description="Full PathState JSON after Manual tool edits.",
    )


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


class StepperBeatResponse(BaseModel):
    id: str
    kind: Literal["measure", "work", "rest"]
    title: str
    counter: CounterResponse | None = None
    duration_sec: int | None = None
    signal: TimerSignal | None = None


class StepperResponse(BaseModel):
    beats: list[StepperBeatResponse] = Field(default_factory=list)


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
    day_locked: bool = Field(
        default=False,
        description=(
            "True when day_offset is beyond the physical-day unlock window "
            "(docs/next/04 §4). Preview only — complete/skip/plugin "
            "mutations are rejected server-side (409) while locked."
        ),
    )
    group_id: UUID | None = None
    group_key: str | None = None
    group_title: str | None = None
    checklist_items: list[ChecklistItemResponse] = Field(default_factory=list)
    plugin_hints: list[str] = Field(
        default_factory=list,
        description=(
            "Create #2 announcements "
            "(timers|timeline|interval|counter|stepper). "
            "Full plugin payloads arrive after Start (#3)."
        ),
    )
    timers: list[TimerResponse] = Field(default_factory=list)
    counter: CounterResponse | None = None
    timeline: ActionTimelineResponse | None = None
    interval_plan: IntervalPlanResponse | None = None
    stepper: StepperResponse | None = None


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
    # Guide Cover (Facio 0.1) — emoji/mark + effort + duration glance.
    cover_emoji: str | None = None
    cover_difficulty: str | None = None
    cover_duration_summary: str | None = None
    cycle: CycleResponse | None = None
    current_day: CurrentDayResponse | None = None
    committed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    next_action: ActionResponse | None = Field(
        default=None,
        description=(
            "Current «Сегодня» step: earliest pending action with "
            "day_offset <= unlocked_day_index (physical-day focus). Null "
            "for draft / completed / abandoned, or while waiting for the "
            "next calendar day (see peek_action)."
        ),
    )
    unlocked_day_index: int | None = Field(
        default=None,
        description=(
            "Execute ceiling: -1 before cycle_anchor_date (nothing unlocked); "
            "else min(local_today - anchor, horizon_days-1). "
            "Null for non-active projects."
        ),
    )
    cycle_anchor_date: date | None = Field(
        default=None,
        description="Calendar date day_offset=0 unlocked (commit date, "
        "+1 when first_step_when=tomorrow).",
    )
    peek_action: ActionResponse | None = Field(
        default=None,
        description=(
            "Read-only preview of the next locked action when there is no "
            "executable next_action today (day done early / waiting on "
            "calendar). Never completable — day_locked is always true."
        ),
    )
    peek_day: CurrentDayResponse | None = Field(
        default=None,
        description="Day framing for peek_action, when present.",
    )
    next_unlock_date: date | None = Field(
        default=None,
        description="Calendar date peek_action becomes executable, when waiting.",
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
            "False while progressive create phase-2 Path skeleton is still "
            "generating (start surface already available)."
        ),
    )
    path_error: str | None = Field(
        default=None,
        description=(
            "Set when phase-2 Path generation failed; client should stop "
            "polling and show an error (not an infinite spinner)."
        ),
    )
    plugins_ready: bool = Field(
        default=True,
        description=(
            "False while phase-3 plugin materialize runs after Start "
            "(actions may still show plugin_hints only)."
        ),
    )
    plugins_error: str | None = Field(
        default=None,
        description=(
            "Set when phase-3 plugin materialize failed; client should stop "
            "polling plugins_ready and show an error with retry."
        ),
    )
    repair_summary: str | None = Field(
        default=None,
        description=(
            "Set only on the response to POST .../repair: short one-line "
            "«what changed» summary (repair-flavored paraphrase) for a "
            "confirmation toast/banner. Not persisted / not present on "
            "plain GET."
        ),
    )
    undo_version: int | None = Field(
        default=None,
        description=(
            "Set on POST .../repair apply and POST .../manual-edit: "
            "state_version to restore via POST .../restore-state for Undo."
        ),
    )
    cycle_result: CycleResultResponse | None = Field(
        default=None,
        description="Structured summary of the finished current cycle.",
    )
    cycles_history: list[CycleHistoryEntry] = Field(
        default_factory=list,
        description="Archived prior cycles (lean) — cycle 1 stays visible.",
    )
    next_cycle_available: bool = Field(
        default=False,
        description="True when the current cycle is finished and N+1 / Repeat CTA may show.",
    )
    can_finish_cycle: bool = Field(
        default=False,
        description=(
            "True when the cycle is active with some progress and the user "
            "may close early via «Завершить цикл»."
        ),
    )
    continue_kind: ContinueKind | None = Field(
        default=None,
        description=(
            "'repeat' for cook / horizon_days=1; 'next' for multi-day "
            "programs. Null when next_cycle_available is false."
        ),
    )
    continue_label: str | None = Field(
        default=None,
        description="Optional model-provided CTA subtitle (copy only).",
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
