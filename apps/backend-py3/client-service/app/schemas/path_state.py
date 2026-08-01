from typing import Literal, get_args

from pydantic import BaseModel, Field, field_validator, model_validator

# Controlled vocab for demand clustering (docs/mvp/04-metrics.md).
PathDomain = Literal[
    "cooking",
    "fitness",
    "learning",
    "home",
    "errands",
    "work",
    "health",
    "finance",
    "social",
    "other",
]

PATH_DOMAINS: frozenset[str] = frozenset(get_args(PathDomain))

DayKind = Literal["train", "rest", "cook_session", "other"]
DAY_KINDS: frozenset[str] = frozenset(get_args(DayKind))

CycleStatus = Literal["draft", "active", "completed", "abandoned"]
CYCLE_STATUSES: frozenset[str] = frozenset(get_args(CycleStatus))

TimerSignal = Literal["nudge", "alert"]
TIMER_SIGNALS: frozenset[str] = frozenset(get_args(TimerSignal))

# Light announcements on create #2 / refine wire (full payloads in #3).
PluginHint = Literal["timers", "timeline", "interval", "counter"]
PLUGIN_HINTS: frozenset[str] = frozenset(get_args(PluginHint))

# Dropped from Path Anthropic wire (grammar size); still on PathAction app model.
_PATH_WIRE_DROP_ACTION_KEYS = frozenset(
    {"timers", "timeline", "interval_plan", "counter"}
)
_PATH_WIRE_DROP_DEFS = frozenset(
    {
        "PathTimer",
        "PathCounter",
        "PathTimeline",
        "PathIntervalPlan",
        "PathClockBeat",
    }
)


class PathChecklistItem(BaseModel):
    id: str | None = Field(
        default=None,
        description="Optional stable id for the checklist row.",
    )
    title: str = Field(min_length=1, description="Checklist line, e.g. eggs.")
    done: bool = Field(default=False, description="Always false on create.")
    sort: int = Field(default=0, ge=0, description="Order inside the action.")


class PathTimer(BaseModel):
    """One timer in a TimerStack (docs/next/04 §5)."""

    id: str | None = Field(
        default=None,
        description="Stable timer id; reuse on refine when same timer.",
    )
    title: str = Field(
        min_length=1,
        description="Timer label, e.g. «Лапша», «Помешать».",
    )
    duration_sec: int = Field(
        ge=1,
        le=86_400,
        description="Duration in seconds.",
    )
    signal: TimerSignal = Field(
        description="nudge (fractional stir) | alert (critical, e.g. pasta).",
    )
    parallel_group: str | None = Field(
        default=None,
        description="Same non-empty key → parallel timers; else sequential UI.",
    )


class PathCounter(BaseModel):
    """Dose / counter plugin (docs/next/04 §5)."""

    label: str | None = Field(
        default=None,
        max_length=80,
        description="Optional label, e.g. «повторы», «подходы».",
    )
    target: int = Field(
        ge=1,
        description="Goal count for this step.",
    )
    current: int = Field(
        default=0,
        ge=0,
        description="Always 0 on create; live progress after Accept.",
    )
    step: int = Field(
        default=1,
        ge=1,
        description="Increment per tap; default 1.",
    )


class PathClockBeat(BaseModel):
    """Shared beat for timeline markers and interval segments (slim wire).

    Timeline: ``sec`` = absolute ``at_sec`` from session start.
    Interval: ``sec`` = segment ``duration_sec``.
    """

    sec: int = Field(
        ge=0,
        le=86_400,
        description="at_sec (timeline) or duration_sec (interval).",
    )
    title: str = Field(min_length=1, description="Beat label.")
    signal: TimerSignal = Field(
        description="nudge | alert.",
    )


class PathTimeline(BaseModel):
    """One session clock axis + markers (docs/next/04 clock family)."""

    duration_sec: int = Field(
        ge=1,
        le=86_400,
        description="Axis length in seconds.",
    )
    markers: list[PathClockBeat] = Field(
        default_factory=list,
        description="Markers; beat.sec = at_sec from start.",
    )


class PathIntervalPlan(BaseModel):
    """Sequential segments with pause/resume (docs/next/04 clock family)."""

    segments: list[PathClockBeat] = Field(
        default_factory=list,
        min_length=1,
        description="Ordered work/rest; beat.sec = duration_sec.",
    )


class PathGroup(BaseModel):
    id: str = Field(
        min_length=1,
        description="Stable section id referenced by actions.",
    )
    title: str = Field(
        min_length=1,
        description="Section title shown in «Весь путь», e.g. Покупки.",
    )
    description: str | None = Field(
        default=None,
        max_length=300,
        description=(
            "Optional: why this phase/section exists (1–2 sentences)."
        ),
    )
    sort: int = Field(default=0, ge=0, description="Section order, 0-based.")


class PathAction(BaseModel):
    id: str | None = Field(
        default=None,
        description="Stable step id; reuse on refine/repair when same step.",
    )
    title: str = Field(
        min_length=1,
        description="What to do (verb + object); shown as «Сегодня» / path step.",
    )
    why: str = Field(
        min_length=1,
        description=(
            "Required. Hero «Почему сейчас» — why this step matters for the "
            "outcome. Never empty, generic filler, or medical/finance guarantees."
        ),
    )
    detail: str | None = Field(
        default=None,
        description=(
            "Concrete how-to (not an essay). Cooking: method/timing. "
            "Prefer checklist_items for shopping lists."
        ),
    )
    estimate_min: int | None = Field(
        default=None,
        ge=0,
        description=(
            "Honest minutes, or null. First action ideally ≤ 30–60 and doable today."
        ),
    )
    day_offset: int | None = Field(
        default=None,
        ge=0,
        description=(
            "Day index within the current cycle (0 = day one). "
            "Must match days[].day_index when days are present."
        ),
    )
    sort: int | None = Field(
        default=None, ge=0, description="Order within path/group."
    )
    group_id: str | None = Field(
        default=None,
        description="Must match groups[].id when set; else null.",
    )
    checklist_items: list[PathChecklistItem] = Field(
        default_factory=list,
        description=(
            "Optional sub-checks inside one step "
            "(prefer over many micro-actions for shopping)."
        ),
    )
    plugin_hints: list[PluginHint] = Field(
        default_factory=list,
        description=(
            "Create #2 / refine: announce tools without payloads. "
            "Values: timers|timeline|interval|counter. Empty [] if none. "
            "Full plugin objects come in materialize #3 after Start."
        ),
    )
    # App / DB / materialize #3 only — NOT on Path Anthropic create/refine wire.
    timers: list[PathTimer] = Field(
        default_factory=list,
        description=(
            "TimerStack for simple manual Start waits. Empty [] when unused."
        ),
    )
    counter: PathCounter | None = Field(
        default=None,
        description="Dose counter for train sets/reps.",
    )
    timeline: PathTimeline | None = Field(
        default=None,
        description="Session axis + markers (cook).",
    )
    interval_plan: PathIntervalPlan | None = Field(
        default=None,
        description="Sequential work/rest segments (fitness circuit).",
    )

    @model_validator(mode="before")
    @classmethod
    def normalize_plugin_stubs(cls, data: object) -> object:
        """Wire stubs for counter / timeline / interval_plan → None."""
        if not isinstance(data, dict):
            return data
        out = dict(data)
        counter = out.get("counter")
        if isinstance(counter, dict):
            target = counter.get("target", -1)
            if target is None or target == -1 or target == "":
                out["counter"] = None
        timeline = out.get("timeline")
        if isinstance(timeline, dict):
            duration = timeline.get("duration_sec", -1)
            markers = timeline.get("markers") or []
            if duration is None or duration == -1 or duration == "" or (
                isinstance(duration, int) and duration < 1 and not markers
            ):
                out["timeline"] = None
        elif timeline is None:
            pass
        interval = out.get("interval_plan")
        if isinstance(interval, dict):
            segments = interval.get("segments") or []
            if not segments:
                out["interval_plan"] = None
        return out


class PathCycle(BaseModel):
    """Current execution cycle for the plan (docs/next/04 §3)."""

    index: int = Field(
        default=1,
        ge=1,
        description="1-based cycle number inside the project.",
    )
    horizon_days: int = Field(
        ge=1,
        le=90,
        description=(
            "Length of this cycle in days. Defaults: cooking/carbonara → 1; "
            "fitness/push-ups → 7."
        ),
    )
    status: CycleStatus = Field(
        default="draft",
        description="draft | active | completed | abandoned.",
    )
    goal_for_cycle: str | None = Field(
        default=None,
        max_length=300,
        description="Optional goal specific to this cycle.",
    )


class PathDay(BaseModel):
    """One scheduled day inside the current cycle (docs/next/04 §4)."""

    day_index: int = Field(
        ge=0,
        description="0-based day within the cycle (0 .. horizon_days-1).",
    )
    kind: DayKind = Field(
        description="train | rest | cook_session | other.",
    )
    title: str | None = Field(
        default=None,
        max_length=120,
        description="Optional day label, e.g. «Силовая A», «Отдых + мобилити».",
    )
    summary: str | None = Field(
        default=None,
        max_length=300,
        description="Short note on what this day is for.",
    )


class ClarifyQuestion(BaseModel):
    id: str = Field(description="Stable question id for refine answers.")
    prompt: str = Field(description="Clarify question shown to the user.")
    options: list[str] = Field(
        default_factory=list,
        description="Chip options; user may still type free text.",
    )


def _default_horizon_days(domain: str | None, actions: list) -> int:
    offsets = [
        a.get("day_offset")
        for a in actions
        if isinstance(a, dict) and a.get("day_offset") is not None
    ]
    if offsets:
        return max(int(o) for o in offsets) + 1
    if domain == "fitness":
        return 7
    if domain == "cooking":
        return 1
    return 1


# Hotfix (fit_sample dogfood): a single cycle must never sprawl into a
# multi-week program. Fitness cycles target/truncate to 7 days; every domain
# hard-caps at 14. Excess days AND actions beyond the cap are dropped — those
# weeks belong in the next cycle, not in a hollow shell of this one.
HORIZON_HARD_CAP = 14
FITNESS_HORIZON_TARGET = 7
_FITNESS_TAG_HINTS = frozenset(
    {"pushup", "pushups", "push-up", "push-ups", "отжимания", "отжимание"}
)


def _is_fitness_like(domain: str | None, tags: list) -> bool:
    if domain == "fitness":
        return True
    return any(
        isinstance(tag, str) and tag.strip().lower() in _FITNESS_TAG_HINTS
        for tag in tags or []
    )


def _acted_day_offsets(actions: list) -> set[int]:
    offsets: set[int] = set()
    for action in actions:
        if not isinstance(action, dict):
            continue
        off = action.get("day_offset")
        if off is None:
            continue
        try:
            offsets.add(int(off))
        except (TypeError, ValueError):
            continue
    return offsets


def _trim_rest_tail(days: list[dict], acted_offsets: set[int]) -> list[dict]:
    """Drop trailing days[] that have no action attached.

    Only the tail is touched — a rest day sandwiched between trained days is
    a deliberate rhythm, not the bug. A hollow run at the *end* (e.g. fit_sample:
    horizon 35, actions only through day 19, days 20–34 empty rest) is the bug.
    """
    if not days or not acted_offsets:
        return days
    ordered = sorted(days, key=lambda d: d.get("day_index", 0))
    while len(ordered) > 1 and ordered[-1].get("day_index") not in acted_offsets:
        ordered.pop()
    return ordered


def _cycle_horizon_cap(domain: str | None, tags: list) -> int:
    """Fitness → 7; everything else → 14. Absolute max is always 14."""
    if _is_fitness_like(domain, tags):
        return FITNESS_HORIZON_TARGET
    return HORIZON_HARD_CAP


def normalize_cycle_horizon(
    domain: str | None,
    tags: list,
    cycle: dict,
    days: list,
    actions: list,
) -> tuple[dict, list, list]:
    """Trim hollow rest tail, then hard-truncate cycle to domain cap.

    Runs on every create / refine / repair parse (see
    ``PathState.backfill_missing_fields``). No-op when ``actions`` is empty
    (progressive create phase-1 skeleton — nothing to trim against yet).

    Returns ``(cycle, days, actions)`` — actions with ``day_offset >= cap``
    are dropped so validators don't see orphan offsets past horizon.
    """
    if not actions or not isinstance(days, list) or not days:
        return cycle, days, actions
    if not all(isinstance(d, dict) for d in days):
        return cycle, days, actions

    acted_offsets = _acted_day_offsets(actions)
    trimmed = _trim_rest_tail(list(days), acted_offsets)

    cap = _cycle_horizon_cap(domain, tags)
    kept_days = [d for d in trimmed if int(d.get("day_index", 0)) < cap]
    if not kept_days:
        kept_days = trimmed[:1]

    kept_actions: list = []
    for action in actions:
        if not isinstance(action, dict):
            kept_actions.append(action)
            continue
        off = action.get("day_offset")
        if off is None:
            kept_actions.append(action)
            continue
        try:
            if int(off) < cap:
                kept_actions.append(action)
        except (TypeError, ValueError):
            kept_actions.append(action)
    if actions and not kept_actions:
        # Extreme edge: every action was past the cap — keep the first so
        # PathState doesn't end up actionless.
        kept_actions = [actions[0]]
        first = kept_actions[0]
        if isinstance(first, dict):
            first = dict(first)
            first["day_offset"] = 0
            kept_actions[0] = first
            if not kept_days:
                kept_days = [
                    {
                        "day_index": 0,
                        "kind": _default_day_kind(domain, 0),
                        "title": None,
                        "summary": None,
                    }
                ]

    cycle = dict(cycle)
    last_day = max((int(d.get("day_index", 0)) for d in kept_days), default=0)
    horizon_days = min(
        int(cycle.get("horizon_days") or (last_day + 1)),
        last_day + 1,
        cap,
    )
    # Keep days[] contiguous 0..horizon-1 after truncate.
    kept_days = [d for d in kept_days if int(d.get("day_index", 0)) < horizon_days]
    cycle["horizon_days"] = max(horizon_days, 1)
    return cycle, kept_days, kept_actions


def _default_day_kind(domain: str | None, day_index: int) -> str:
    if domain == "cooking":
        return "cook_session"
    if domain == "fitness":
        # Alternate train / rest starting with train on day 0.
        return "train" if day_index % 2 == 0 else "rest"
    return "other"


class PathState(BaseModel):
    """Structured LLM output for create / refine / repair."""

    title: str = Field(
        min_length=1,
        max_length=120,
        description=(
            "Plan hero title (one short line). Shown at the start of the "
            "plan body on draft/accept — not a todo dump."
        ),
    )
    summary: str = Field(
        min_length=1,
        max_length=600,
        description=(
            "1–3 sentences at the start of the plan body: what the cycle "
            "delivers and the logic of stages. Never empty on create."
        ),
    )
    outcome: str = Field(
        min_length=1,
        description="Clear goal the user is buying (1 short sentence).",
    )
    paraphrase: str = Field(
        min_length=1,
        description=(
            'Soft-start UI line confirming understanding, e.g. '
            '"Ок — ведём к: …". Warmer than outcome. Match user language.'
        ),
    )
    success_criteria: str = Field(
        min_length=1,
        description=(
            "Verifiable definition of done. No guaranteed health/finance outcomes."
        ),
    )
    horizon: str = Field(
        min_length=1,
        description='Rough span/load, e.g. "1 evening", "2 weeks, ~20 min/day".',
    )
    domain: PathDomain = Field(
        default="other",
        description=(
            "Primary demand domain from controlled vocab "
            "(cooking|fitness|learning|home|errands|work|health|finance|"
            "social|other). Use other when unsure or safety grey-zone."
        ),
    )
    tags: list[str] = Field(
        default_factory=list,
        max_length=5,
        description="0–5 short slugs for clustering (e.g. pasta, dinner).",
    )
    cycle: PathCycle = Field(
        description=(
            "Current cycle: index, horizon_days, status. Required on create; "
            "cooking → short (1); fitness push-ups → ~7."
        ),
    )
    days: list[PathDay] = Field(
        default_factory=list,
        description=(
            "Explicit day map for the cycle (kind train|rest|cook_session|other). "
            "Actions attach via day_offset == day_index."
        ),
    )
    groups: list[PathGroup] = Field(
        default_factory=list,
        description="Optional Path sections (Покупки, Готовка, …).",
    )
    actions: list[PathAction] = Field(
        default_factory=list,
        max_length=16,
        description=(
            "Ordered steps (0 while progressive create loads; then 1–16 soft "
            "cap; prefer ≤12). Every action needs why. First step doable today "
            "when possible. Attach to days via day_offset."
        ),
    )
    questions: list[ClarifyQuestion] = Field(
        default_factory=list,
        max_length=4,
        description=(
            "0 or 2–4 clarifies that materially change the path; max 4. "
            "Empty if path is already enough."
        ),
    )
    resources: list[str] = Field(
        default_factory=list,
        description="Optional materials. Never invent URLs.",
    )
    milestones: list[str] = Field(
        default_factory=list,
        description="Optional checkpoint labels.",
    )

    @model_validator(mode="before")
    @classmethod
    def backfill_missing_fields(cls, data: object) -> object:
        """Older state_json may lack narrative / cycle / days — derive."""
        if not isinstance(data, dict):
            return data
        out = dict(data)
        if out.get("title") is None or "title" not in out:
            out["title"] = out.get("outcome") or "Plan"
        if out.get("summary") is None or "summary" not in out:
            out["summary"] = (
                out.get("success_criteria")
                or out.get("horizon")
                or out.get("outcome")
                or out["title"]
            )

        actions = out.get("actions") if isinstance(out.get("actions"), list) else []
        domain = out.get("domain") if isinstance(out.get("domain"), str) else None

        cycle = out.get("cycle")
        if isinstance(cycle, PathCycle):
            cycle = cycle.model_dump()
        elif not isinstance(cycle, dict):
            cycle = {}
        else:
            cycle = dict(cycle)
        if "index" not in cycle or cycle.get("index") is None:
            cycle["index"] = 1
        if "horizon_days" not in cycle or cycle.get("horizon_days") is None:
            cycle["horizon_days"] = _default_horizon_days(domain, actions)
        if "status" not in cycle or cycle.get("status") is None:
            cycle["status"] = "draft"
        out["cycle"] = cycle

        days = out.get("days")
        if isinstance(days, list) and days and not isinstance(days[0], dict):
            days = [
                d.model_dump() if hasattr(d, "model_dump") else d for d in days
            ]
            out["days"] = days
        if not isinstance(days, list) or len(days) == 0:
            horizon = int(cycle["horizon_days"])
            offsets: set[int] = set()
            for action in actions:
                if not isinstance(action, dict):
                    continue
                off = action.get("day_offset")
                if off is None:
                    offsets.add(0)
                else:
                    offsets.add(int(off))
            if not offsets:
                offsets = {0}
            # Ensure contiguous skeleton 0..horizon-1 for fitness/cooking maps.
            for i in range(horizon):
                offsets.add(i)
            synthesized: list[dict] = []
            for day_index in sorted(offsets):
                if day_index >= horizon:
                    # Expand horizon if actions reference a later day.
                    horizon = day_index + 1
                    cycle["horizon_days"] = horizon
                    out["cycle"] = cycle
                synthesized.append(
                    {
                        "day_index": day_index,
                        "kind": _default_day_kind(domain, day_index),
                        "title": None,
                        "summary": None,
                    }
                )
            out["days"] = synthesized

        tags = out.get("tags") if isinstance(out.get("tags"), list) else []
        out["cycle"], out["days"], out["actions"] = normalize_cycle_horizon(
            domain, tags, out["cycle"], out["days"], actions
        )

        return out

    @field_validator("questions")
    @classmethod
    def questions_count(cls, value: list[ClarifyQuestion]) -> list[ClarifyQuestion]:
        # Allow [] (enough already) or 2–4; reject a lone idle question.
        if len(value) == 1:
            raise ValueError(
                "questions must be empty or have 2–4 items (got 1)"
            )
        return value

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, value: list[str]) -> list[str]:
        cleaned: list[str] = []
        seen: set[str] = set()
        for raw in value:
            tag = raw.strip().lower().replace(" ", "-")
            if not tag or tag in seen:
                continue
            seen.add(tag)
            cleaned.append(tag[:48])
            if len(cleaned) >= 5:
                break
        return cleaned

    @field_validator("title", "summary")
    @classmethod
    def strip_narrative(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("must be non-empty")
        return cleaned

    @model_validator(mode="after")
    def validate_path(self) -> "PathState":
        group_ids = {g.id for g in self.groups}
        if len(group_ids) != len(self.groups):
            raise ValueError("groups[].id must be unique")

        day_indexes = [d.day_index for d in self.days]
        if len(day_indexes) != len(set(day_indexes)):
            raise ValueError("days[].day_index must be unique")
        for day in self.days:
            if day.day_index >= self.cycle.horizon_days:
                raise ValueError(
                    f"days[].day_index {day.day_index} exceeds "
                    f"cycle.horizon_days {self.cycle.horizon_days}"
                )

        day_index_set = set(day_indexes)
        for action in self.actions:
            if not action.why.strip():
                raise ValueError("action.why must be non-empty")
            if action.group_id is not None and action.group_id not in group_ids:
                raise ValueError(
                    f"action.group_id '{action.group_id}' has no matching group"
                )
            if action.day_offset is not None and day_index_set:
                if action.day_offset not in day_index_set:
                    raise ValueError(
                        f"action.day_offset {action.day_offset} has no matching "
                        "days[].day_index"
                    )
            for item in action.checklist_items:
                if not item.title.strip():
                    raise ValueError("checklist_items.title must be non-empty")
            for timer in action.timers:
                if not timer.title.strip():
                    raise ValueError("timers.title must be non-empty")
            if action.counter is not None and action.counter.current < 0:
                raise ValueError("counter.current must be >= 0")
            if action.timeline is not None:
                for marker in action.timeline.markers:
                    if not marker.title.strip():
                        raise ValueError("timeline.markers.title must be non-empty")
                    if marker.sec > action.timeline.duration_sec:
                        raise ValueError(
                            "timeline.markers.sec must be <= duration_sec"
                        )
            if action.interval_plan is not None:
                if not action.interval_plan.segments:
                    raise ValueError("interval_plan.segments must be non-empty")
                for segment in action.interval_plan.segments:
                    if not segment.title.strip():
                        raise ValueError(
                            "interval_plan.segments.title must be non-empty"
                        )
                    if segment.sec < 1:
                        raise ValueError(
                            "interval_plan.segments.sec must be >= 1"
                        )
        return self


class ActionPluginPayload(BaseModel):
    """One action's executable plugins (materialize #3 wire)."""

    action_id: str = Field(
        min_length=1,
        description="Must match PathState actions[].id (stable key).",
    )
    timers: list[PathTimer] = Field(
        default_factory=list,
        description="TimerStack; empty [] when unused.",
    )
    # Wire stubs → None in normalize (same sentinels as legacy Path wire).
    counter: PathCounter | None = Field(
        default=None,
        description=(
            "Dose counter. Wire: always emit object; "
            "target=-1 means absent."
        ),
    )
    timeline: PathTimeline | None = Field(
        default=None,
        description=(
            "Session axis. Wire: always emit; duration_sec=-1 means absent."
        ),
    )
    interval_plan: PathIntervalPlan | None = Field(
        default=None,
        description=(
            "Circuit segments. Wire: always emit; empty segments means absent."
        ),
    )

    @model_validator(mode="before")
    @classmethod
    def normalize_plugin_stubs(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data
        out = dict(data)
        counter = out.get("counter")
        if isinstance(counter, dict):
            target = counter.get("target", -1)
            if target is None or target == -1 or target == "":
                out["counter"] = None
        timeline = out.get("timeline")
        if isinstance(timeline, dict):
            duration = timeline.get("duration_sec", -1)
            markers = timeline.get("markers") or []
            if duration is None or duration == -1 or duration == "" or (
                isinstance(duration, int) and duration < 1 and not markers
            ):
                out["timeline"] = None
        interval = out.get("interval_plan")
        if isinstance(interval, dict):
            segments = interval.get("segments") or []
            if not segments:
                out["interval_plan"] = None
        return out


class ActionPluginsMaterialize(BaseModel):
    """Create #3 response: fill plugins for hinted actions."""

    actions: list[ActionPluginPayload] = Field(
        default_factory=list,
        description=(
            "Plugin payloads for actions that had plugin_hints. "
            "Prefer all hinted actions in the cycle (MVP)."
        ),
    )


def _path_llm_schema() -> dict:
    """Structured-output schema for Anthropic Path create #2 / refine / repair.

    Drop ``resources`` / ``milestones`` and full plugin objects (timers /
    timeline / interval_plan / counter) — grammar budget. Actions carry
    ``plugin_hints`` only; payloads materialize in a separate #3 call.
    """
    schema = PathState.model_json_schema()
    props = schema.get("properties")
    if isinstance(props, dict):
        props.pop("resources", None)
        props.pop("milestones", None)
    required = schema.get("required")
    if isinstance(required, list):
        schema["required"] = [
            key for key in required if key not in ("resources", "milestones")
        ]

    defs = schema.get("$defs") or schema.get("definitions")
    if isinstance(defs, dict):
        action = defs.get("PathAction")
        if isinstance(action, dict):
            action_props = action.get("properties")
            if isinstance(action_props, dict):
                for key in _PATH_WIRE_DROP_ACTION_KEYS:
                    action_props.pop(key, None)
            action_req = action.get("required")
            if isinstance(action_req, list):
                action["required"] = [
                    key
                    for key in action_req
                    if key not in _PATH_WIRE_DROP_ACTION_KEYS
                ]
        for def_name in _PATH_WIRE_DROP_DEFS:
            defs.pop(def_name, None)
    return schema


def _plugins_materialize_schema() -> dict:
    """Tiny schema for create #3 — action_id → full plugin payloads."""
    return ActionPluginsMaterialize.model_json_schema()


# Used for Anthropic structured outputs (create path phase, refine, repair).
PATH_RESPONSE_SCHEMA: dict = _path_llm_schema()
# Create #3 after Start — full plugin objects, no Path skeleton.
PLUGINS_MATERIALIZE_SCHEMA: dict = _plugins_materialize_schema()
