from __future__ import annotations

from datetime import datetime

from facio_domain.drift import drift_card, is_drifting, next_drift_offer, silence_days
from facio_domain.fixtures import instances_from_rows
from facio_domain.models import (
    Cadence,
    DriftAskState,
    DriftOffer,
    Instance,
    Subject,
    SubjectStatus,
)


def _instance(subject_id: str, when: str, status: str = "completed") -> Instance:
    return Instance(
        id=f"{subject_id}-{when}",
        subject_id=subject_id,
        when=datetime.fromisoformat(when),
        status=status,  # type: ignore[arg-type]
    )


def test_bike_silence_thresholds(bike: Subject, scenarios: dict, now: datetime) -> None:
    for case in scenarios["bike_silence"]:
        instances = [_instance("bike", case["last_completed"])]
        assert is_drifting(bike, instances, now) is case["expect_drifting"], case["id"]
        assert silence_days(bike, instances, now) == (
            now.date() - datetime.fromisoformat(case["last_completed"]).date()
        ).days


def test_cadence_none_without_instances_is_not_drift(now: datetime) -> None:
    one_off = Subject(id="gift", title="one gift", cadence=Cadence.none())
    assert is_drifting(one_off, [], now) is False


def test_never_started_subject_is_not_drift(bike: Subject, now: datetime) -> None:
    assert is_drifting(bike, [], now) is False


def test_miss_tuesday_is_not_drift(
    push_ups: Subject, scenarios: dict, now: datetime
) -> None:
    instances = instances_from_rows(scenarios["miss_tuesday"]["instances"])
    assert is_drifting(push_ups, instances, now) is False


def test_retired_subject_is_not_drifting(bike: Subject, now: datetime) -> None:
    retired = bike.model_copy(update={"status": SubjectStatus.retired})
    instances = [_instance("bike", "2026-07-25T18:00:00")]
    assert is_drifting(retired, instances, now) is False


def test_drift_card_picks_oldest_silence(
    bike: Subject, vegetables: Subject, now: datetime
) -> None:
    instances = [
        _instance("bike", "2026-07-25T18:00:00"),
        _instance("vegetables", "2026-08-11T12:00:00"),
    ]
    card = drift_card([bike, vegetables], instances, now)
    assert card is not None
    assert card.subject_id == "bike"
    assert card.silent_days == 21
    assert card.offer == DriftOffer.move_to_today


def test_next_drift_offer_ladder() -> None:
    assert next_drift_offer(0, 0) == DriftOffer.move_to_today
    assert next_drift_offer(1, 0) == DriftOffer.once_a_week
    assert next_drift_offer(2, 0) == DriftOffer.retire
    assert next_drift_offer(3, 1) == DriftOffer.retire
    assert next_drift_offer(4, 2) == DriftOffer.stop


def test_drift_card_uses_history(bike: Subject, now: datetime) -> None:
    instances = [_instance("bike", "2026-08-07T18:00:00")]
    card = drift_card(
        [bike],
        instances,
        now,
        histories={"bike": DriftAskState(asks_made=2, retire_refusals=2)},
    )
    assert card is not None
    assert card.offer == DriftOffer.stop


def test_prepared_instance_does_not_break_silence(bike: Subject, now: datetime) -> None:
    instances = [
        _instance("bike", "2026-07-25T18:00:00"),
        _instance("bike", "2026-08-20T19:00:00", status="prepared"),
    ]
    assert is_drifting(bike, instances, now) is True
