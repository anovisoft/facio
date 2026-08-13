"""Unit tests for repair plugin preserve vs strip (Slice E dogfood fix)."""

from copy import deepcopy

from app.schemas.path_state import PathState
from app.services.path import _prepare_repair_state
from app.services.path_materialize import path_plugins_ready
from app.services.repair_diff import build_repair_diff
from tests.factories import (
    _sample_train_stepper,
    sample_fitness_path_state,
)


def _prior_with_filled_stepper() -> PathState:
    payload = sample_fitness_path_state(questions=[])
    for action in payload["actions"]:
        if action.get("plugin_hints") == ["stepper"]:
            action["stepper"] = _sample_train_stepper(measure_target=15)
    return PathState.model_validate(payload)


def _llm_hints_only_wire(*, title: str = "Лёгкая силовая") -> PathState:
    """What repair LLM returns: plugin_hints only, no payloads."""
    payload = sample_fitness_path_state(
        questions=[],
        paraphrase="Облегчили сегодняшнюю нагрузку",
    )
    for action in payload["actions"]:
        if action.get("id") == "d0":
            action["title"] = title
        action["stepper"] = None
        action["counter"] = None
        action["timeline"] = None
        action["interval_plan"] = None
        action["timers"] = []
    return PathState.model_validate(payload)


def test_prepare_shift_preserves_stepper():
    prior = _prior_with_filled_stepper()
    new = _llm_hints_only_wire()
    prepared = _prepare_repair_state(prior, new, "shift")
    d0 = next(a for a in prepared.actions if a.id == "d0")
    assert d0.stepper is not None
    assert d0.plugin_hints == ["stepper"]
    assert path_plugins_ready(prepared) is True


def test_prepare_none_intent_preserves_like_shift():
    prior = _prior_with_filled_stepper()
    new = _llm_hints_only_wire()
    prepared = _prepare_repair_state(prior, new, None)
    d0 = next(a for a in prepared.actions if a.id == "d0")
    assert d0.stepper is not None
    assert path_plugins_ready(prepared) is True


def test_prepare_lighten_strips_stepper_keeps_hints():
    prior = _prior_with_filled_stepper()
    new = _llm_hints_only_wire()
    prepared = _prepare_repair_state(prior, new, "lighten")
    d0 = next(a for a in prepared.actions if a.id == "d0")
    assert d0.stepper is None
    assert d0.plugin_hints == ["stepper"]
    assert path_plugins_ready(prepared) is False


def test_prepare_rest_strips_stepper_keeps_hints():
    prior = _prior_with_filled_stepper()
    new = _llm_hints_only_wire(title="Лёгкая мобилити")
    prepared = _prepare_repair_state(prior, new, "rest")
    d0 = next(a for a in prepared.actions if a.id == "d0")
    assert d0.stepper is None
    assert d0.plugin_hints == ["stepper"]
    assert path_plugins_ready(prepared) is False


def test_prepare_lighten_infers_hints_when_llm_dropped_them():
    prior = _prior_with_filled_stepper()
    new_payload = sample_fitness_path_state(questions=[])
    for action in new_payload["actions"]:
        action["plugin_hints"] = []
        action["stepper"] = None
    new = PathState.model_validate(new_payload)
    prepared = _prepare_repair_state(prior, new, "lighten")
    d0 = next(a for a in prepared.actions if a.id == "d0")
    assert d0.stepper is None
    assert d0.plugin_hints == ["stepper"]
    assert path_plugins_ready(prepared) is False


def test_diff_shows_load_rematerialize_line_when_plugins_stripped():
    prior = _prior_with_filled_stepper()
    after = _prepare_repair_state(prior, _llm_hints_only_wire(), "lighten")
    lines = build_repair_diff(prior, after)
    assert any(
        line["before"] == "Previous load (sets)"
        and "tool updates" in line["after"]
        for line in lines
    )


def test_diff_no_load_line_when_shift_preserves():
    prior = _prior_with_filled_stepper()
    after_payload = deepcopy(sample_fitness_path_state(questions=[]))
    # Shift day 0 action to day 1 — preserve will keep stepper.
    for action in after_payload["actions"]:
        if action["id"] == "d0":
            action["day_offset"] = 1
            action["stepper"] = None  # hints-only wire
    after_wire = PathState.model_validate(after_payload)
    after = _prepare_repair_state(prior, after_wire, "shift")
    lines = build_repair_diff(prior, after)
    assert not any(line["before"] == "Previous load (sets)" for line in lines)
