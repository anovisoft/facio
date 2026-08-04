"""Unit tests for human-readable Repair Diff (Facio 0.1 Slice E)."""

from app.schemas.path_state import PathState
from app.services.repair_diff import build_repair_diff
from tests.factories import sample_fitness_path_state, sample_path_state


def test_diff_action_title_and_day_shift():
    before = PathState.model_validate(sample_path_state(questions=[]))
    after_payload = sample_path_state(
        questions=[],
        paraphrase="Сдвинули готовку",
        actions=[
            {
                **a,
                "day_offset": (a.get("day_offset") or 0) + 1,
                "title": (
                    "Лёгкая готовка"
                    if a.get("id") == "cook"
                    else a["title"]
                ),
            }
            for a in sample_path_state()["actions"]
        ],
    )
    # Ensure cycle horizon covers shifted days
    after_payload["cycle"]["horizon_days"] = max(
        after_payload["cycle"]["horizon_days"],
        max(a["day_offset"] for a in after_payload["actions"]) + 1,
    )
    after_payload["days"] = [
        {
            "day_index": 0,
            "kind": "cook_session",
            "title": "День 1",
            "summary": "",
        },
        {
            "day_index": 1,
            "kind": "cook_session",
            "title": "День 2",
            "summary": "",
        },
    ]
    after = PathState.model_validate(after_payload)
    lines = build_repair_diff(before, after)
    assert any(line["before"].startswith("Day ") for line in lines)
    assert any(
        line["before"] != line["after"] and "Лёгкая" in line["after"]
        for line in lines
    )


def test_diff_day_kind_change_fitness():
    before = PathState.model_validate(sample_fitness_path_state())
    after_payload = sample_fitness_path_state()
    # Flip day 0 to rest
    after_payload["days"][0]["kind"] = "rest"
    after_payload["days"][0]["title"] = "Отдых"
    after = PathState.model_validate(after_payload)
    lines = build_repair_diff(before, after)
    assert lines
    assert any("Отдых" in line["after"] or "rest" in line["after"] for line in lines)


def test_diff_fallback_when_structure_same():
    before = PathState.model_validate(
        sample_path_state(questions=[], paraphrase="Was")
    )
    after = PathState.model_validate(
        sample_path_state(
            questions=[],
            paraphrase="Moved today's workout to tomorrow",
            summary="Slightly different summary for the plan",
        )
    )
    lines = build_repair_diff(before, after)
    assert len(lines) >= 1
    assert lines[0]["before"] != lines[0]["after"]
