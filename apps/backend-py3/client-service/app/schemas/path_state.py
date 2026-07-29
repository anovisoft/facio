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


class PathChecklistItem(BaseModel):
    id: str | None = Field(
        default=None,
        description="Optional stable id for the checklist row.",
    )
    title: str = Field(min_length=1, description="Checklist line, e.g. eggs.")
    done: bool = Field(default=False, description="Always false on create.")
    sort: int = Field(default=0, ge=0, description="Order inside the action.")


class PathGroup(BaseModel):
    id: str = Field(
        min_length=1,
        description="Stable section id referenced by actions.",
    )
    title: str = Field(
        min_length=1,
        description="Section title shown in «Весь путь», e.g. Покупки.",
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
        description="Days from first step (0 = day one), or null.",
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


class ClarifyQuestion(BaseModel):
    id: str = Field(description="Stable question id for refine answers.")
    prompt: str = Field(description="Clarify question shown to the user.")
    options: list[str] = Field(
        default_factory=list,
        description="Chip options; user may still type free text.",
    )


class PathState(BaseModel):
    """Structured LLM output for create / refine / repair."""

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
    groups: list[PathGroup] = Field(
        default_factory=list,
        description="Optional Path sections (Покупки, Готовка, …).",
    )
    actions: list[PathAction] = Field(
        min_length=1,
        max_length=12,
        description=(
            "Ordered steps (1–12 soft cap). Every action needs why. "
            "First step doable today when possible."
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
