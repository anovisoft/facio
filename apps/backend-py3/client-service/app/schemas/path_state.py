from pydantic import BaseModel, Field, model_validator


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
