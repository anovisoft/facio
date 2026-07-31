from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.path_state import PathDomain, PathState


class InstantAnswerPayload(BaseModel):
    label: str = Field(
        min_length=1,
        description=(
            "Short UI line: this looks like a question, not a goal. "
            "Match user language."
        ),
    )
    answer: str = Field(
        min_length=1,
        description=(
            "Direct useful answer — or a short safe refusal/redirect "
            "(no harm instructions; no medical diagnosis)."
        ),
    )
    goal_suggestions: list[str] = Field(
        min_length=2,
        max_length=4,
        description=(
            "Exactly 2–4 related goals that ARE sequences over time "
            "(Facio projects), not more questions."
        ),
    )
    domain: PathDomain = Field(
        default="other",
        description="Same controlled domain vocab as path (for Q&A demand).",
    )


class InstantAnswerWire(BaseModel):
    """Gate wire shape — empty stub allowed when kind=path."""

    label: str = ""
    answer: str = ""
    goal_suggestions: list[str] = Field(default_factory=list)
    domain: PathDomain = "other"


class ClarifyQuestionWire(BaseModel):
    """Slim clarify chip for create start surface (no PathState bloat)."""

    id: str = ""
    prompt: str = ""
    options: list[str] = Field(default_factory=list)


class PathStartSurface(BaseModel):
    """Validated start surface when kind=path (phase 1)."""

    paraphrase: str = Field(min_length=1)
    title: str = Field(min_length=1, max_length=120)
    summary: str = Field(min_length=1, max_length=600)
    questions: list[ClarifyQuestionWire] = Field(default_factory=list, max_length=4)
    # Short day titles only (e.g. "Силовая A") — NO plugins / full day schema.
    outline_days: list[str] = Field(default_factory=list, max_length=8)

    @model_validator(mode="after")
    def validate_questions(self) -> "PathStartSurface":
        n = len(self.questions)
        if n == 1:
            raise ValueError("questions must be empty or have 2–4 items (got 1)")
        days = [d.strip() for d in self.outline_days if d.strip()]
        questions = [
            q
            for q in self.questions
            if q.id.strip() and q.prompt.strip()
        ]
        return self.model_copy(update={"outline_days": days, "questions": questions})


class PathStartSurfaceWire(BaseModel):
    """Anthropic wire for path start — always emit object (stub when IA)."""

    paraphrase: str = ""
    title: str = ""
    summary: str = ""
    questions: list[ClarifyQuestionWire] = Field(default_factory=list)
    outline_days: list[str] = Field(default_factory=list)


class CreateGateResponse(BaseModel):
    """Create gate + optional start surface (no PathState / plugins).

    Anthropic structured-output grammar cannot fit PathState + InstantAnswer
    in one schema after Slice 3 plugins. Gate decides kind and, for path,
    returns a slim start surface; full Path is a second call.
    """

    kind: Literal["path", "instant_answer"]
    instant_answer: InstantAnswerPayload | None = None
    path_start: PathStartSurface | None = None

    @model_validator(mode="after")
    def validate_branch(self) -> "CreateGateResponse":
        if self.kind == "instant_answer":
            if self.instant_answer is None:
                raise ValueError(
                    "instant_answer is required when kind=instant_answer"
                )
            if self.path_start is not None:
                return self.model_copy(update={"path_start": None})
        elif self.kind == "path":
            if self.path_start is None:
                raise ValueError("path_start is required when kind=path")
            if self.instant_answer is not None:
                return self.model_copy(update={"instant_answer": None})
        else:
            raise ValueError(f"Unknown kind: {self.kind!r}")
        return self


class CreateGateWire(BaseModel):
    """Anthropic wire for create gate — always emit both branch objects."""

    kind: Literal["path", "instant_answer"]
    instant_answer: InstantAnswerWire
    path_start: PathStartSurfaceWire


class CreateLlmResponse(BaseModel):
    """Assembled create result (gate + optional path). Not sent to Anthropic."""

    kind: Literal["path", "instant_answer"] = Field(
        description=(
            'Use "path" if the intent needs a sequence of actions over time; '
            '"instant_answer" for one-shot Q&A/facts, grey-zone unsure cases, '
            "or safety refusal. Never a harmful path."
        )
    )
    path: PathState | None = Field(
        default=None,
        description="Filled when kind=path; null when kind=instant_answer.",
    )
    instant_answer: InstantAnswerPayload | None = Field(
        default=None,
        description="Filled when kind=instant_answer; null when kind=path.",
    )

    @model_validator(mode="after")
    def validate_branch(self) -> "CreateLlmResponse":
        if self.kind == "path":
            if self.path is None:
                raise ValueError("path is required when kind=path")
        elif self.kind == "instant_answer":
            if self.instant_answer is None:
                raise ValueError(
                    "instant_answer is required when kind=instant_answer"
                )
        else:
            raise ValueError(f"Unknown kind: {self.kind!r}")
        return self


CREATE_GATE_SCHEMA: dict = CreateGateWire.model_json_schema()
# Legacy dual-branch schema — kept for unit tests of CreateLlmResponse shape.
# Not used for Anthropic calls (grammar too large with Path plugins).
CREATE_RESPONSE_SCHEMA: dict = CreateLlmResponse.model_json_schema()
