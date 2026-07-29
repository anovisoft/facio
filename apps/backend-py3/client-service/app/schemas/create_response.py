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


class CreateLlmResponse(BaseModel):
    """Structured LLM output for purpose=create (path | instant_answer)."""

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


CREATE_RESPONSE_SCHEMA: dict = CreateLlmResponse.model_json_schema()
