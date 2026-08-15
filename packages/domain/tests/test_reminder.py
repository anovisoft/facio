from __future__ import annotations

from datetime import date, time

from facio_domain.reminder import reminder_fire_at, window_from_closing


def test_closing_22_fires_at_19(bike) -> None:
    window = window_from_closing(time(22, 0))
    assert window.closes_at == time(22, 0)
    assert window.latest_by == time(19, 0)
    fired = reminder_fire_at(bike, window, date(2026, 8, 15))
    assert fired.hour == 19
    assert fired.minute == 0
    assert fired.date() == date(2026, 8, 15)


def test_bike_fixture_window_matches_founding_rule(bike) -> None:
    assert bike.window is not None
    derived = window_from_closing(bike.window.closes_at)
    assert derived.latest_by == bike.window.latest_by
    fired = reminder_fire_at(bike, bike.window, date(2026, 8, 15))
    assert fired.isoformat() == "2026-08-15T19:00:00"
