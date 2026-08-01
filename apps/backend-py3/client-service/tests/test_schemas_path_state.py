import pytest
from pydantic import ValidationError

from app.schemas.path_state import PathState
from tests.factories import sample_path_state


def test_valid_path_state():
    state = PathState.model_validate(sample_path_state())
    assert state.title
    assert state.summary
    assert state.outcome
    assert state.domain == "cooking"
    assert len(state.actions) == 3
    assert all(a.why.strip() for a in state.actions)


def test_empty_why_rejected():
    payload = sample_path_state()
    payload["actions"][0]["why"] = "   "
    with pytest.raises(ValidationError, match="why"):
        PathState.model_validate(payload)


def test_single_question_rejected():
    payload = sample_path_state()
    payload["questions"] = [
        {"id": "q1", "prompt": "Only one?", "options": ["a"]},
    ]
    with pytest.raises(ValidationError, match="2–4"):
        PathState.model_validate(payload)


def test_empty_questions_ok():
    state = PathState.model_validate(sample_path_state(questions=[]))
    assert state.questions == []


def test_unknown_group_id_rejected():
    payload = sample_path_state()
    payload["actions"][0]["group_id"] = "missing"
    with pytest.raises(ValidationError, match="group_id"):
        PathState.model_validate(payload)


def test_tags_normalized_and_deduped():
    payload = sample_path_state(
        tags=[" Pasta ", "pasta", "Dinner", "Extra Tag"]
    )
    state = PathState.model_validate(payload)
    assert state.tags == ["pasta", "dinner", "extra-tag"]


def test_tags_max_five_rejected():
    payload = sample_path_state(
        tags=["a", "b", "c", "d", "e", "f"]
    )
    with pytest.raises(ValidationError):
        PathState.model_validate(payload)


def test_invalid_domain_rejected():
    payload = sample_path_state(domain="spaceships")
    with pytest.raises(ValidationError):
        PathState.model_validate(payload)


def test_empty_actions_allowed_for_progressive_start():
    """Phase-1 start surface may persist with actions=[] (path_ready=false)."""
    payload = sample_path_state(actions=[])
    state = PathState.model_validate(payload)
    assert state.actions == []


def test_missing_title_summary_backfilled_from_contract():
    payload = sample_path_state()
    del payload["title"]
    del payload["summary"]
    state = PathState.model_validate(payload)
    assert state.title == payload["outcome"]
    assert state.summary == payload["success_criteria"]


def test_empty_title_rejected():
    payload = sample_path_state(title="   ")
    with pytest.raises(ValidationError):
        PathState.model_validate(payload)


def test_group_description_optional():
    state = PathState.model_validate(sample_path_state())
    assert state.groups[0].description
    payload = sample_path_state()
    payload["groups"][0]["description"] = None
    cleared = PathState.model_validate(payload)
    assert cleared.groups[0].description is None


def test_cycle_and_days_present():
    state = PathState.model_validate(sample_path_state())
    assert state.cycle.horizon_days == 1
    assert state.cycle.status == "draft"
    assert len(state.days) == 1
    assert state.days[0].kind == "cook_session"


def test_cycle_days_backfilled_from_legacy_payload():
    payload = sample_path_state()
    del payload["cycle"]
    del payload["days"]
    state = PathState.model_validate(payload)
    assert state.cycle.horizon_days == 1
    assert state.days[0].kind == "cook_session"
    assert state.days[0].day_index == 0


def test_fitness_week_has_train_and_rest():
    from tests.factories import sample_fitness_path_state

    state = PathState.model_validate(sample_fitness_path_state())
    assert state.cycle.horizon_days == 7
    kinds = {d.kind for d in state.days}
    assert "train" in kinds
    assert "rest" in kinds
    assert len(state.days) == 7


def test_action_day_offset_must_match_day():
    payload = sample_path_state()
    payload["actions"][0]["day_offset"] = 3
    with pytest.raises(ValidationError, match="day_offset"):
        PathState.model_validate(payload)


def test_duplicate_day_index_rejected():
    payload = sample_path_state()
    payload["days"] = [
        {"day_index": 0, "kind": "cook_session"},
        {"day_index": 0, "kind": "other"},
    ]
    with pytest.raises(ValidationError, match="day_index"):
        PathState.model_validate(payload)


# --- Hotfix: horizon clamp + rest-tail trim (fit_sample dogfood) ----------


def test_carbonara_horizon_one_not_regressed():
    """Cooking / horizon=1 must not regress from the new normalize step."""
    state = PathState.model_validate(sample_path_state())
    assert state.cycle.horizon_days == 1
    assert len(state.days) == 1


def test_fitness_week_seven_not_regressed():
    from tests.factories import sample_fitness_path_state

    state = PathState.model_validate(sample_fitness_path_state())
    assert state.cycle.horizon_days == 7
    assert len(state.days) == 7
    assert max(a.day_offset for a in state.actions) == 6


def test_fitness_overshoot_trims_hollow_rest_tail():
    """fit_sample bug: horizon 35, actions only through day 19, days 20-34
    empty rest. Trim drops the hollow tail; fitness hard-truncate then keeps
    only the first week (days 0–6) — later weeks belong in the next cycle."""
    from tests.factories import sample_fitness_overshoot_path_state

    payload = sample_fitness_overshoot_path_state()
    assert payload["cycle"]["horizon_days"] == 35
    assert len(payload["days"]) == 35

    state = PathState.model_validate(payload)

    assert state.cycle.horizon_days == 7
    assert len(state.days) == 7
    assert max(d.day_index for d in state.days) == 6
    assert max(a.day_offset for a in state.actions if a.day_offset is not None) == 6
    assert all(
        a.day_offset is None or a.day_offset < 7 for a in state.actions
    )


def test_generic_domain_hard_cap_trims_declared_horizon():
    """Non-fitness domain: model declares horizon_days=30 but the days[] map
    it actually emitted only spans 14 days (last one has a real action) —
    the global hard cap reins the inflated number back to match, instead of
    persisting a hollow month-long horizon."""
    payload = sample_path_state(domain="learning")
    payload["cycle"]["horizon_days"] = 30
    payload["days"] = [
        {"day_index": i, "kind": "other", "title": None, "summary": None}
        for i in range(14)
    ]
    for action in payload["actions"]:
        action["day_offset"] = 13

    state = PathState.model_validate(payload)

    assert state.cycle.horizon_days == 14
    assert len(state.days) == 14


def test_fitness_domain_truncates_actions_past_week():
    """Fitness overshoot with real actions on days 7–9 is truncated to week 1
    (horizon 7) — excess actions belong in the next cycle."""
    from tests.factories import sample_fitness_path_state

    payload = sample_fitness_path_state()
    extra_days = [
        {
            "day_index": i,
            "kind": "train" if i % 2 == 0 else "rest",
            "title": None,
            "summary": None,
        }
        for i in range(7, 10)
    ]
    payload["days"] = payload["days"] + extra_days
    payload["cycle"]["horizon_days"] = 10
    extra_actions = [
        {
            "id": f"extra{i}",
            "title": "Подходы отжиманий",
            "why": "Продолжаем неделю",
            "detail": None,
            "estimate_min": 15,
            "day_offset": i,
            "sort": i,
            "group_id": None,
            "checklist_items": [],
            "plugin_hints": [],
            "timers": [],
            "counter": None,
            "timeline": None,
            "interval_plan": None,
            "stepper": None,
        }
        for i in range(7, 10)
    ]
    payload["actions"] = payload["actions"] + extra_actions

    state = PathState.model_validate(payload)

    assert state.cycle.horizon_days == 7
    assert len(state.days) == 7
    assert all(
        a.day_offset is None or a.day_offset < 7 for a in state.actions
    )
    assert not any(a.id.startswith("extra") for a in state.actions)


def test_progressive_start_skeleton_untouched_with_no_actions():
    """Phase-1 draft (actions=[]) must not be trimmed/clamped — nothing to
    trim against yet, and the outline should render as-is."""
    payload = sample_path_state(actions=[])
    payload["cycle"]["horizon_days"] = 8
    payload["days"] = [
        {"day_index": i, "kind": "other", "title": None, "summary": None}
        for i in range(8)
    ]
    state = PathState.model_validate(payload)
    assert state.cycle.horizon_days == 8
    assert len(state.days) == 8


# --- Stepper beat counter normalize (Slice 4′ dogfood) ----------------------


def _fitness_action_with_stepper(beats: list) -> dict:
    from tests.factories import sample_fitness_path_state

    payload = sample_fitness_path_state()
    for action in payload["actions"]:
        if action.get("plugin_hints") == ["stepper"] or action.get("stepper"):
            action["plugin_hints"] = ["stepper"]
            action["stepper"] = {"beats": beats}
            action["counter"] = None
            break
    return payload


def test_measure_beat_without_counter_validates_after_normalize():
    """LLM #3 sometimes omits counter on measure/work — soft-fill target=1."""
    payload = _fitness_action_with_stepper(
        [
            {
                "id": "m0",
                "kind": "measure",
                "title": "Замер",
                "counter": None,
                "duration_sec": None,
                "signal": "nudge",
            },
            {
                "id": "r0",
                "kind": "rest",
                "title": "Отдых",
                "counter": None,
                "duration_sec": 90,
                "signal": "nudge",
            },
            {
                "id": "w1",
                "kind": "work",
                "title": "Подход 1",
                "counter": {
                    "label": "",
                    "target": -1,
                    "current": 0,
                    "step": 1,
                },
                "duration_sec": -1,
                "signal": "nudge",
            },
        ]
    )
    state = PathState.model_validate(payload)
    train = next(a for a in state.actions if a.stepper is not None)
    assert train.stepper is not None
    measure, rest, work = train.stepper.beats
    assert measure.counter is not None
    assert measure.counter.target == 1
    assert measure.counter.current == 0
    assert rest.counter is None
    assert rest.duration_sec == 90
    assert work.counter is not None
    assert work.counter.target == 1


def test_action_plugin_payload_fills_measure_stub_counter():
    from app.schemas.path_state import ActionPluginPayload

    payload = ActionPluginPayload.model_validate(
        {
            "action_id": "a0",
            "timers": [],
            "counter": {"label": "", "target": -1, "current": 0, "step": 1},
            "timeline": {"duration_sec": -1, "markers": []},
            "interval_plan": {"segments": []},
            "stepper": {
                "beats": [
                    {
                        "id": "m0",
                        "kind": "measure",
                        "title": "Max",
                        "counter": {
                            "label": "",
                            "target": -1,
                            "current": 0,
                            "step": 1,
                        },
                        "duration_sec": -1,
                        "signal": "nudge",
                    }
                ]
            },
        }
    )
    assert payload.stepper is not None
    beat = payload.stepper.beats[0]
    assert beat.counter is not None
    assert beat.counter.target == 1
    assert payload.counter is None


def test_normalize_stepper_beats_helper():
    from app.schemas.path_state import normalize_stepper_beats

    beats = normalize_stepper_beats(
        [
            {"kind": "measure", "title": "M", "counter": None},
            {
                "kind": "rest",
                "title": "R",
                "counter": {"target": -1, "current": 0, "step": 1},
                "duration_sec": -1,
            },
        ]
    )
    assert beats[0]["counter"]["target"] == 1
    assert beats[1]["counter"] is None
    assert beats[1]["duration_sec"] is None
