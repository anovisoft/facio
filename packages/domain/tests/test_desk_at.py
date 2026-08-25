from __future__ import annotations

from datetime import datetime, timedelta

from facio_domain.desk import founding_desk
from facio_domain.desk_at import render


def test_render_shows_drift_card_after_silence() -> None:
    origin = datetime(2026, 8, 25, 9, 0, 0)
    desk = founding_desk(now=origin)
    later = origin + timedelta(days=21)

    result = render(desk, later)

    assert result["drift_card"]["subject_id"] == "bike"
    assert result["drift_card"]["silent_days"] >= 21
    assert all(item["subject_id"] == "bike" for item in result["today"])


def test_render_horizon_has_seven_days() -> None:
    now = datetime(2026, 8, 25, 9, 0, 0)
    desk = founding_desk(now=now)

    result = render(desk, now)

    assert len(result["horizon"]["days"]) == 7
    assert result["horizon"]["days"][0]["date"] == "2026-08-25"
