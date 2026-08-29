from __future__ import annotations

from datetime import datetime, timedelta

from facio_domain.drift import (
    answer_drift,
    answers_the_ladder,
    can_ask_now,
    drift_card,
    is_drifting,
    next_drift_offer,
    next_offer,
    refuse_drift,
    settle_talk_answer,
    silence_days,
)
from facio_domain.fixtures import instances_from_rows
from facio_domain.models import (
    Cadence,
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


def _silent_bike(bike: Subject, **ladder: object) -> tuple[Subject, list[Instance]]:
    """A weekly practice 21 days quiet, standing on whatever rung is asked for."""
    return bike.model_copy(update=ladder), [_instance("bike", "2026-07-25T18:00:00")]


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


def test_paused_subject_is_not_drifting(bike: Subject, now: datetime) -> None:
    paused = bike.model_copy(
        update={"status": SubjectStatus.paused, "paused_at": now}
    )
    instances = [_instance("bike", "2026-07-25T18:00:00")]
    assert is_drifting(paused, instances, now) is False


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


# --- Q28: the ladder -------------------------------------------------------


def test_next_drift_offer_walks_the_fixture_ladder(scenarios: dict) -> None:
    for case in scenarios["drift_ladder"]:
        assert next_drift_offer(case["asks_made"], case["retire_refusals"]) == case[
            "expect_offer"
        ], case["id"]


def test_ladder_reads_off_the_subject(bike: Subject) -> None:
    assert next_offer(bike) == DriftOffer.move_to_today
    assert next_offer(bike.model_copy(update={"drift_asks_made": 1})) == DriftOffer.once_a_week
    assert next_offer(bike.model_copy(update={"drift_asks_made": 2})) == DriftOffer.retire
    silenced = bike.model_copy(update={"drift_asks_made": 4, "drift_retire_refusals": 2})
    assert next_offer(silenced) == DriftOffer.stop


def test_ladder_never_climbs_back_up(bike: Subject) -> None:
    """Every rung is less commitment than the last. Volume never rises (#21)."""
    rungs = [
        next_offer(bike.model_copy(update={"drift_asks_made": step})) for step in range(3)
    ]
    assert rungs == [DriftOffer.move_to_today, DriftOffer.once_a_week, DriftOffer.retire]
    order = {DriftOffer.move_to_today: 0, DriftOffer.once_a_week: 1, DriftOffer.retire: 2}
    assert [order[rung] for rung in rungs] == sorted(order[rung] for rung in rungs)


def test_one_ask_per_cadence_period(bike: Subject, now: datetime) -> None:
    assert can_ask_now(bike, now) is True
    asked = bike.model_copy(update={"drift_asked_at": now, "drift_asks_made": 1})
    assert can_ask_now(asked, now) is False
    assert can_ask_now(asked, now + timedelta(days=7)) is False
    # Eight days is a full weekly period of silence: the same ask, once more.
    assert can_ask_now(asked, now + timedelta(days=8)) is True


def test_daily_subject_waits_its_own_shorter_period(
    vegetables: Subject, now: datetime
) -> None:
    asked = vegetables.model_copy(update={"drift_asked_at": now, "drift_asks_made": 1})
    assert can_ask_now(asked, now + timedelta(days=2)) is False
    assert can_ask_now(asked, now + timedelta(days=3)) is True


def test_two_refusals_are_enough_to_go_quiet(bike: Subject, now: datetime) -> None:
    """Refuse the offer to retire twice and the product stops asking (Q28)."""
    subject, instances = _silent_bike(bike, drift_asks_made=2)
    assert next_offer(subject) == DriftOffer.retire

    once = refuse_drift(subject, DriftOffer.retire, now)
    assert once.drift_retire_refusals == 1
    assert next_offer(once) == DriftOffer.retire

    later = now + timedelta(days=8)
    twice = refuse_drift(once, DriftOffer.retire, later)
    assert twice.drift_retire_refusals == 2
    assert next_offer(twice) == DriftOffer.stop
    assert can_ask_now(twice, later + timedelta(days=365)) is False
    # Alive in Deeds, without a rhythm. Nothing deleted, nothing hidden.
    assert twice.status == SubjectStatus.active
    assert twice.cadence.is_none
    assert twice.instance_ids == subject.instance_ids
    assert twice.cue_ids == subject.cue_ids
    assert drift_card([twice], instances, later + timedelta(days=30)) is None


def test_refusing_a_lower_rung_does_not_count_as_a_retire_refusal(
    bike: Subject, now: datetime
) -> None:
    refused = refuse_drift(bike, DriftOffer.move_to_today, now)
    assert refused.drift_retire_refusals == 0
    assert refused.drift_asks_made == 1
    assert next_offer(refused) == DriftOffer.once_a_week


def test_answer_move_to_today_changes_no_commitment(
    bike: Subject, now: datetime
) -> None:
    answered = answer_drift(bike, DriftOffer.move_to_today, now)
    assert answered.cadence == bike.cadence
    assert answered.status == bike.status
    assert answered.drift_asks_made == 1
    assert answered.drift_asked_at == now


def test_answer_once_a_week_shrinks_the_rhythm(bike: Subject, now: datetime) -> None:
    answered = answer_drift(bike, DriftOffer.once_a_week, now)
    assert answered.cadence == Cadence.of(1, "week")
    assert answered.status == SubjectStatus.shrunk
    assert answered.drift_asks_made == 1


def test_answer_retire_keeps_history(bike: Subject, now: datetime) -> None:
    answered = answer_drift(bike, DriftOffer.retire, now)
    assert answered.status == SubjectStatus.retired
    assert answered.cue_ids == bike.cue_ids
    assert answered.instance_ids == bike.instance_ids


def test_answering_hides_the_card_until_the_next_period(
    bike: Subject, now: datetime
) -> None:
    subject, instances = _silent_bike(bike)
    card = drift_card([subject], instances, now)
    assert card is not None and card.offer == DriftOffer.move_to_today

    answered = answer_drift(subject, DriftOffer.move_to_today, now)
    assert drift_card([answered], instances, now) is None
    assert drift_card([answered], instances, now + timedelta(days=7)) is None
    later = drift_card([answered], instances, now + timedelta(days=8))
    assert later is not None
    assert later.offer == DriftOffer.once_a_week


def test_one_card_even_when_three_subjects_drift(
    bike: Subject, push_ups: Subject, vegetables: Subject, now: datetime
) -> None:
    instances = [
        _instance("bike", "2026-07-25T18:00:00"),
        _instance("push-ups", "2026-08-01T08:00:00"),
        _instance("vegetables", "2026-08-05T12:00:00"),
    ]
    card = drift_card([bike, push_ups, vegetables], instances, now)
    assert card is not None
    assert card.subject_id == "bike"


def test_a_quiet_subject_does_not_block_the_one_behind_it(
    bike: Subject, push_ups: Subject, now: datetime
) -> None:
    """Asked-this-period is filtered before the oldest wins, not after."""
    instances = [
        _instance("bike", "2026-07-25T18:00:00"),
        _instance("push-ups", "2026-08-01T08:00:00"),
    ]
    asked_bike = bike.model_copy(update={"drift_asked_at": now, "drift_asks_made": 1})
    card = drift_card([asked_bike, push_ups], instances, now)
    assert card is not None
    assert card.subject_id == "push-ups"


def test_paused_subject_is_not_asked(bike: Subject, now: datetime) -> None:
    """Pause is a boundary, not a rung: a frozen practice hears nothing (В2.3)."""
    subject, instances = _silent_bike(bike)
    paused = subject.model_copy(
        update={"status": SubjectStatus.paused, "paused_at": now}
    )
    assert drift_card([paused], instances, now) is None


def test_prepared_instance_does_not_break_silence(bike: Subject, now: datetime) -> None:
    instances = [
        _instance("bike", "2026-07-25T18:00:00"),
        _instance("bike", "2026-08-20T19:00:00", status="prepared"),
    ]
    assert is_drifting(bike, instances, now) is True


# --- Q28: the mouth can answer the ladder too -------------------------------


def test_shrinking_in_talk_spends_this_periods_ask(bike: Subject, now: datetime) -> None:
    """Said it out loud, so the card does not ask it again the same morning."""
    subject, instances = _silent_bike(bike)
    assert drift_card([subject], instances, now) is not None

    smaller = subject.model_copy(update={"cadence": Cadence.of(1, "week")})
    settled = settle_talk_answer(subject, smaller, now)
    assert settled.drift_asked_at == now
    assert drift_card([settled], instances, now) is None


def test_talk_answer_does_not_climb_the_ladder(bike: Subject, now: datetime) -> None:
    """A rung is bought with a refusal, not with doing the thing (#21)."""
    subject, instances = _silent_bike(bike)
    smaller = subject.model_copy(update={"cadence": Cadence.of(1, "week")})
    settled = settle_talk_answer(subject, smaller, now)
    assert settled.drift_asks_made == subject.drift_asks_made
    assert settled.drift_retire_refusals == subject.drift_retire_refusals
    assert next_offer(settled) == DriftOffer.move_to_today


def test_next_period_asks_the_same_rung_after_a_talk_answer(
    bike: Subject, now: datetime
) -> None:
    subject, instances = _silent_bike(bike)
    settled = settle_talk_answer(
        subject, subject.model_copy(update={"cadence": Cadence.of(1, "week")}), now
    )
    assert drift_card([settled], instances, now + timedelta(days=7)) is None
    later = drift_card([settled], instances, now + timedelta(days=8))
    assert later is not None
    # Same rung, not the louder one an increment would have handed out.
    assert later.offer == DriftOffer.move_to_today


def test_growing_the_rhythm_in_talk_is_not_an_answer(
    bike: Subject, now: datetime
) -> None:
    """The silence did not go away because the promise got bigger."""
    subject, instances = _silent_bike(bike)
    louder = subject.model_copy(update={"cadence": Cadence.of(5, "week")})
    settled = settle_talk_answer(subject, louder, now)
    assert settled.drift_asked_at is None
    assert drift_card([settled], instances, now) is not None


def test_retiring_and_freezing_in_talk_are_answers(bike: Subject, now: datetime) -> None:
    for update in (
        {"status": SubjectStatus.retired},
        {"status": SubjectStatus.paused, "paused_at": now},
        {"status": SubjectStatus.shrunk},
    ):
        after = bike.model_copy(update=update)
        assert answers_the_ladder(bike, after) is True
        assert settle_talk_answer(bike, after, now).drift_asked_at == now


def test_freeze_stamps_the_period_so_thaw_counts_from_the_talk(
    bike: Subject, now: datetime
) -> None:
    """Paused cannot drift, but the clock must start at the conversation."""
    subject, instances = _silent_bike(bike)
    paused = settle_talk_answer(
        subject,
        subject.model_copy(update={"status": SubjectStatus.paused, "paused_at": now}),
        now,
    )
    assert paused.drift_asked_at == now
    back = paused.model_copy(update={"status": SubjectStatus.active, "paused_at": None})
    assert settle_talk_answer(paused, back, now).drift_asked_at == now
    assert drift_card([back], instances, now + timedelta(days=1)) is None
    assert drift_card([back], instances, now + timedelta(days=8)) is not None


def test_coming_back_is_not_a_step_down(bike: Subject, now: datetime) -> None:
    paused = bike.model_copy(update={"status": SubjectStatus.paused, "paused_at": now})
    thawed = paused.model_copy(update={"status": SubjectStatus.active, "paused_at": None})
    assert answers_the_ladder(paused, thawed) is False


def test_moving_one_instance_is_not_an_answer(bike: Subject, now: datetime) -> None:
    """`move_to_date` moves a card; the promise stays exactly as big."""
    assert answers_the_ladder(bike, bike) is False
    assert settle_talk_answer(bike, bike, now).drift_asked_at is None


def test_refusal_from_the_card_still_moves_the_rung(bike: Subject, now: datetime) -> None:
    subject, _instances = _silent_bike(bike)
    refused = refuse_drift(subject, DriftOffer.move_to_today, now)
    assert refused.drift_asks_made == 1
    assert next_offer(refused) == DriftOffer.once_a_week
