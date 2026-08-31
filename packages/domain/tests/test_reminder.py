from __future__ import annotations

from datetime import date, time

import pytest
from pydantic import ValidationError

from facio_domain.models import Window
from facio_domain.reminder import reminder_fire_at, reminder_fire_times, window_from_closing


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


def test_a_window_may_hold_several_stated_hours(bike) -> None:
    """Q34: «в 10, 12, 15, 16:30, 18, 21, 22» is one window, seven hours."""
    window = Window(hours=[time(15, 0), time(10, 0), time(16, 30), time(12, 0)])
    assert window.hours == [time(10, 0), time(12, 0), time(15, 0), time(16, 30)]
    assert window.latest_by == time(10, 0)
    fired = reminder_fire_times(window, date(2026, 8, 15))
    assert [moment.strftime("%H:%M") for moment in fired] == ["10:00", "12:00", "15:00", "16:30"]
    assert reminder_fire_at(bike, window, date(2026, 8, 15)) == fired[0]


def test_a_window_written_before_q34_still_opens() -> None:
    """The old shape on disk and on the wire: one `latest_by`, no `hours`."""
    window = Window.model_validate({"latest_by": "19:00:00", "closes_at": "22:00:00"})
    assert window.hours == [time(19, 0)]
    assert window.latest_by == time(19, 0)
    assert window.closes_at == time(22, 0)
    # And it goes back out in the shape an older client reads.
    dumped = window.model_dump(mode="json")
    assert dumped["latest_by"] == "19:00:00"
    assert dumped["hours"] == ["19:00:00"]


def test_a_window_with_no_hour_is_not_a_window() -> None:
    with pytest.raises(ValidationError):
        Window(closes_at=time(22, 0))


def test_the_same_hour_twice_is_one_hour() -> None:
    window = Window(hours=[time(10, 0), time(10, 0)], latest_by=time(10, 0))
    assert window.hours == [time(10, 0)]


def test_next_hour_is_the_nearest_one_still_ahead() -> None:
    window = Window(hours=[time(10, 0), time(12, 0), time(22, 0)])
    assert window.next_hour(time(9, 0)) == time(10, 0)
    assert window.next_hour(time(11, 0)) == time(12, 0)
    assert window.next_hour(time(12, 0)) == time(12, 0)
    # The day is spent: the face falls back to the first hour of the next one.
    assert window.next_hour(time(23, 0)) == time(10, 0)
