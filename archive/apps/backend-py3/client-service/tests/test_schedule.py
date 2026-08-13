"""Physical-day gate helpers (docs/next/04 §4, docs/next/09 decision E)."""

from datetime import date, datetime, timedelta, timezone

import pytest

from app.errors import ValidationAppError
from app.services.schedule import (
    day_unlock_date,
    is_day_locked,
    parse_local_date,
    resolve_cycle_anchor,
    unlocked_day_index,
)


def test_parse_local_date_parses_iso():
    assert parse_local_date("2026-07-31") == date(2026, 7, 31)


def test_parse_local_date_none_falls_back_to_utc_today():
    assert parse_local_date(None) == datetime.now(timezone.utc).date()


def test_parse_local_date_blank_falls_back_to_utc_today():
    assert parse_local_date("   ") == datetime.now(timezone.utc).date()


def test_parse_local_date_rejects_garbage():
    with pytest.raises(ValidationAppError):
        parse_local_date("not-a-date")


def test_resolve_cycle_anchor_today_is_commit_date():
    committed = datetime(2026, 7, 31, 20, 0, tzinfo=timezone.utc)
    assert resolve_cycle_anchor(
        committed_at=committed, first_step_when="today"
    ) == date(2026, 7, 31)


def test_resolve_cycle_anchor_tomorrow_adds_a_day():
    committed = datetime(2026, 7, 31, 20, 0, tzinfo=timezone.utc)
    assert resolve_cycle_anchor(
        committed_at=committed, first_step_when="tomorrow"
    ) == date(2026, 8, 1)


def test_unlocked_day_index_clamps_to_horizon():
    anchor = date(2026, 7, 1)
    # Same day as anchor → day 0 unlocked.
    assert unlocked_day_index(
        anchor=anchor, horizon_days=7, local_today=anchor
    ) == 0
    # Mid-cycle: local_today - anchor days unlocked.
    assert unlocked_day_index(
        anchor=anchor, horizon_days=7, local_today=anchor + timedelta(days=3)
    ) == 3
    # Past the horizon: clamp to horizon_days - 1, never auto-advances beyond.
    assert unlocked_day_index(
        anchor=anchor, horizon_days=7, local_today=anchor + timedelta(days=30)
    ) == 6
    # Before the anchor (e.g. first_step_when=tomorrow): nothing executable.
    assert unlocked_day_index(
        anchor=anchor, horizon_days=7, local_today=anchor - timedelta(days=2)
    ) == -1


def test_unlocked_day_index_carbonara_horizon_one_never_regresses():
    anchor = date(2026, 7, 1)
    for offset in (0, 1, 5, 100):
        assert (
            unlocked_day_index(
                anchor=anchor,
                horizon_days=1,
                local_today=anchor + timedelta(days=offset),
            )
            == 0
        )


def test_unlocked_day_index_missing_anchor_fully_unlocks_legacy_projects():
    # Pre-Slice-4 projects committed before the migration have no anchor —
    # must not lock them out.
    assert (
        unlocked_day_index(anchor=None, horizon_days=7, local_today=date.today())
        == 6
    )


def test_day_unlock_date_adds_offset_to_anchor():
    anchor = date(2026, 7, 1)
    assert day_unlock_date(anchor, 3) == date(2026, 7, 4)
    assert day_unlock_date(None, 3) is None
    assert day_unlock_date(anchor, None) is None


def test_is_day_locked():
    assert is_day_locked(3, unlocked=2) is True
    assert is_day_locked(2, unlocked=2) is False
    assert is_day_locked(0, unlocked=2) is False
    assert is_day_locked(None, unlocked=2) is False
    assert is_day_locked(0, unlocked=-1) is True
    assert is_day_locked(None, unlocked=-1) is False
