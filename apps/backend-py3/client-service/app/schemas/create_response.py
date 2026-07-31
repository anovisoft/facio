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


class CreateGateResponse(BaseModel):
    """Tiny create gate: path vs instant_answer (no PathState).

    Anthropic structured-output grammar cannot fit PathState + InstantAnswer
    in one schema after Slice 3 plugins. Gate decides kind; path body is a
    second call with PATH_RESPONSE_SCHEMA only.
    """

    kind: Literal["path", "instant_answer"]
    instant_answer: InstantAnswerPayload | None = None

    @model_validator(mode="after")
    def validate_branch(self) -> "CreateGateResponse":
        if self.kind == "instant_answer":
            if self.instant_answer is None:
                raise ValueError(
                    "instant_answer is required when kind=instant_answer"
                )
        elif self.kind == "path":
            # Drop accidental stubs; path body comes from the second LLM call.
            if self.instant_answer is not None:
                return self.model_copy(update={"instant_answer": None})
        else:
            raise ValueError(f"Unknown kind: {self.kind!r}")
        return self


class CreateGateWire(BaseModel):
    """Anthropic wire for create gate — always emit instant_answer object."""

    kind: Literal["path", "instant_answer"]
    instant_answer: InstantAnswerWire


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
