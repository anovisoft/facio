"""Unit tests for the validation-retry nudge (fit_sample hotfix, item C.3)."""

from app.services.path import _retry_hint


def test_actions_overflow_mentions_horizon_and_actions():
    exc = ValueError(
        "actions\n  List should have at most 16 items after validation, "
        "not 19 [type=too_long, ...]"
    )
    hint = _retry_hint(exc)
    assert hint
    assert "actions" in hint
    assert "horizon_days" in hint


def test_days_overflow_also_triggers_hint():
    exc = ValueError(
        "days\n  List should have at most 30 items after validation, "
        "not 35 [type=too_long, ...]"
    )
    hint = _retry_hint(exc)
    assert hint
    assert "horizon_days" in hint


def test_unrelated_error_gets_no_extra_hint():
    exc = ValueError("action.why must be non-empty")
    assert _retry_hint(exc) == ""
