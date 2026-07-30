"""Cycle / schedule helpers and next-action day ordering."""

from uuid import uuid4

from app.models import Action, ActionStatus, Project, ProjectStatus
from app.schemas.api import ActionResponse, CycleResponse, DayResponse
from app.schemas.path_state import PathState
from app.services.path_llm import (
    _FEWSHOT_FITNESS,
    _FEWSHOT_PATH,
    parse_create_response,
)
from app.services.serializers import (
    action_queue_key,
    pick_next_action,
    resolve_current_day,
)
from tests.factories import sample_fitness_path_state, sample_path_state


def test_fewshots_parse_as_create_responses():
    carbonara = parse_create_response(_FEWSHOT_PATH)
    assert carbonara.kind == "path"
    assert carbonara.path is not None
    assert carbonara.path.cycle.horizon_days == 1
    assert carbonara.path.days[0].kind == "cook_session"

    fitness = parse_create_response(_FEWSHOT_FITNESS)
    assert fitness.kind == "path"
    assert fitness.path is not None
    assert fitness.path.cycle.horizon_days == 7
    kinds = {d.kind for d in fitness.path.days}
    assert kinds == {"train", "rest"}


def test_pick_next_action_prefers_earliest_day():
    project = Project(
        id=uuid4(),
        user_id=uuid4(),
        status=ProjectStatus.active,
        raw_intent="push",
    )
    later = Action(
        id=uuid4(),
        project_id=project.id,
        key="d2",
        title="Day 2",
        why="later",
        sort=0,
        day_offset=2,
        status=ActionStatus.pending,
    )
    earlier = Action(
        id=uuid4(),
        project_id=project.id,
        key="d0",
        title="Day 0",
        why="first",
        sort=1,
        day_offset=0,
        status=ActionStatus.pending,
    )
    project.actions = [later, earlier]
    next_action = pick_next_action(project)
    assert next_action is not None
    assert next_action.key == "d0"
    assert action_queue_key(later) > action_queue_key(earlier)


def test_resolve_current_day_from_next_action():
    cycle = CycleResponse(index=1, horizon_days=7, status="active")
    days = [
        DayResponse(day_index=0, kind="train", title="A", summary=None),
        DayResponse(day_index=1, kind="rest", title="Rest", summary="Recover"),
    ]
    next_action = ActionResponse(
        id=uuid4(),
        project_id=uuid4(),
        title="Mobility",
        why="rest day",
        detail=None,
        estimate_min=10,
        due_at=None,
        sort=1,
        status="pending",
        day_offset=1,
        checklist_items=[],
    )
    current = resolve_current_day(
        cycle=cycle, days=days, next_action=next_action
    )
    assert current is not None
    assert current.day_number == 2
    assert current.kind == "rest"
    assert current.title == "Rest"


def test_fitness_state_validates():
    state = PathState.model_validate(sample_fitness_path_state())
    assert state.cycle.horizon_days == 7
    assert len(state.actions) == 7


def test_carbonara_state_short_cycle():
    state = PathState.model_validate(sample_path_state())
    assert state.cycle.horizon_days == 1
    assert all(a.day_offset == 0 for a in state.actions)
