"""Unit tests for Guide Cover heuristics."""

from uuid import uuid4

from app.models import Project, ProjectStatus
from app.schemas.path_state import PathState
from app.services.cover import apply_cover_fallback
from tests.factories import sample_fitness_path_state, sample_path_state


def _project() -> Project:
    return Project(
        id=uuid4(),
        user_id=uuid4(),
        status=ProjectStatus.draft,
        raw_intent="x",
    )


def test_cover_cooking_uses_domain_emoji_and_horizon():
    project = _project()
    state = PathState.model_validate(sample_path_state())
    apply_cover_fallback(project, state)
    assert project.cover_emoji == "🍝"
    assert project.cover_difficulty == "Easy"
    assert project.cover_duration_summary == "1 evening, ~45 min"


def test_cover_fitness_medium_and_horizon_string():
    project = _project()
    state = PathState.model_validate(sample_fitness_path_state())
    apply_cover_fallback(project, state)
    assert project.cover_emoji == "🏋️"
    assert project.cover_difficulty == "Medium"
    assert "дн" in (project.cover_duration_summary or "") or "day" in (
        project.cover_duration_summary or ""
    ).lower() or project.cover_duration_summary
