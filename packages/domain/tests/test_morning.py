"""Q6: the morning card fires on a delta or on drift, and never on nothing."""

from __future__ import annotations

from datetime import date, datetime, time

from facio_domain.fixtures import instances_from_rows
from facio_domain.groups import group_key
from facio_domain.lid import lid_projection
from facio_domain.models import (
    Cadence,
    DeltaTodayItem,
    Instance,
    InstanceStatus,
    Subject,
    SubjectStatus,
    Widget,
    WidgetPayload,
    WidgetSection,
    WidgetStatus,
    WidgetTodayItem,
    WidgetType,
    Window,
)
from facio_domain.morning import (
    delta_card,
    done_in_period,
    morning_delta,
    period_days,
    promised,
)


def _instance(subject_id: str, when: str, status: str = "completed") -> Instance:
    return Instance(
        id=f"{subject_id}-{when}",
        subject_id=subject_id,
        when=datetime.fromisoformat(when),
        status=status,  # type: ignore[arg-type]
    )


def _widget(
    subject_id: str,
    *,
    status: WidgetStatus = WidgetStatus.ready,
    section: WidgetSection = WidgetSection.today,
) -> Widget:
    return Widget(
        id=f"{subject_id}-tile",
        type=WidgetType.counter,
        title=subject_id,
        payload=WidgetPayload(),
        status=status,
        section=section,
        subject_id=subject_id,
        instance_id=f"{subject_id}-inst",
    )


def test_period_length_and_promise(push_ups: Subject, vegetables: Subject) -> None:
    assert period_days(push_ups.cadence) == 7
    assert period_days(vegetables.cadence) == 1
    assert period_days(Cadence.none()) is None
    assert promised(push_ups.cadence) == 3
    assert promised(Cadence.none()) == 0


def test_delta_is_promised_minus_done(push_ups: Subject, now: datetime) -> None:
    instances = [
        _instance("push-ups", "2026-08-10T08:00:00"),
        _instance("push-ups", "2026-08-14T08:00:00"),
    ]
    assert done_in_period(push_ups, instances, now) == 2
    assert morning_delta(push_ups, instances, now) == 1


def test_work_outside_the_period_does_not_count(
    push_ups: Subject, now: datetime
) -> None:
    """A trailing period, so last month's sets do not pay this week's promise."""
    old = [_instance("push-ups", "2026-07-20T08:00:00")]
    assert done_in_period(push_ups, old, now) == 0


def test_doing_more_than_promised_is_not_a_debt(
    vegetables: Subject, now: datetime
) -> None:
    instances = [
        _instance("vegetables", "2026-08-15T09:00:00"),
        _instance("vegetables", "2026-08-15T19:00:00"),
    ]
    assert morning_delta(vegetables, instances, now) == 0


def test_empty_day_without_delta_or_drift_stays_empty(
    subjects, scenarios: dict, now: datetime
) -> None:
    case = scenarios["empty_today_no_commitments"]
    instances = instances_from_rows(case["instances"])
    projection = lid_projection(now, subjects, instances, [])
    assert projection.today == []
    assert projection.drift_card is None
    assert projection.delta_card is None


def test_delta_alone_puts_one_calm_card_on_today(
    subjects, scenarios: dict, now: datetime
) -> None:
    case = scenarios["empty_today_with_delta"]
    instances = instances_from_rows(case["instances"])
    projection = lid_projection(now, subjects, instances, [])
    assert projection.drift_card is None
    card = projection.delta_card
    assert card is not None
    assert card.subject_id == case["expect_delta_subject"]
    assert card.promised == case["expect_delta_promised"]
    assert card.done == case["expect_delta_done"]
    assert card.remaining == case["expect_delta_remaining"]
    assert [item.kind for item in projection.today] == case["expect_today_kinds"]
    assert isinstance(projection.today[0], DeltaTodayItem)


def test_drift_beats_delta_so_the_morning_says_one_thing(
    subjects, scenarios: dict, now: datetime
) -> None:
    case = scenarios["empty_today_with_drift"]
    instances = instances_from_rows(case["instances"])
    projection = lid_projection(now, subjects, instances, [])
    assert projection.drift_card is not None
    assert projection.delta_card is None
    assert [item.kind for item in projection.today] == case["expect_today_kinds"]


def test_a_practice_that_never_ran_owes_nothing(subjects, now: datetime) -> None:
    assert delta_card(subjects, [], [], now) is None


def test_a_tile_already_on_today_is_the_delta(push_ups: Subject, now: datetime) -> None:
    instances = [_instance("push-ups", "2026-08-14T08:00:00")]
    assert delta_card([push_ups], instances, [], now) is not None
    live = [_widget("push-ups")]
    assert delta_card([push_ups], instances, live, now) is None


def test_a_done_tile_does_not_cancel_the_rest_of_the_week(
    push_ups: Subject, now: datetime
) -> None:
    instances = [_instance("push-ups", "2026-08-14T08:00:00")]
    done = [_widget("push-ups", status=WidgetStatus.done)]
    card = delta_card([push_ups], instances, done, now)
    assert card is not None
    assert card.remaining == 2


def test_paused_and_retired_practices_owe_nothing(
    push_ups: Subject, now: datetime
) -> None:
    instances = [_instance("push-ups", "2026-08-14T08:00:00")]
    for status in (SubjectStatus.paused, SubjectStatus.retired):
        frozen = push_ups.model_copy(update={"status": status})
        assert delta_card([frozen], instances, [], now) is None


def test_biggest_shortfall_wins_when_two_practices_are_behind(
    push_ups: Subject, bike: Subject, now: datetime
) -> None:
    instances = [
        _instance("push-ups", "2026-08-14T08:00:00"),
        _instance("bike", "2026-08-13T18:00:00"),
    ]
    card = delta_card([push_ups, bike], instances, [], now)
    assert card is not None
    assert card.subject_id == "push-ups"
    assert card.remaining == 2


def test_seven_checks_a_day_are_short_of_seven_not_of_one() -> None:
    """Q34: the delta counts against the count, whatever the count is."""
    subject = Subject(
        id="upwork",
        title="проверить upwork",
        cadence=Cadence.of(7, "day"),
    )
    now = datetime.fromisoformat("2026-08-15T23:00:00")
    done = [_instance("upwork", f"2026-08-15T1{hour}:00:00") for hour in range(3)]
    assert promised(subject.cadence) == 7
    assert done_in_period(subject, done, now) == 3
    card = delta_card([subject], done, [], now)
    assert card is not None
    assert (card.promised, card.done, card.remaining) == (7, 3, 4)


# --- R19 reaches the morning too --------------------------------------------


def test_yesterdays_group_does_not_silence_todays_delta() -> None:
    """A tile the lid refuses to draw must not answer for today (R19).

    R19 stopped a closed day's checks from being *drawn* on Today. The morning
    kept counting them: `_has_live_tile_today` saw seven `ready` tiles in the
    `today` section, decided the practice was already asking, and swallowed the
    delta line. The result on the second morning was a practice with no tile
    **and** no line — «7 обещано, 0 сделано» computed and then thrown away.
    """
    hours = [time(10), time(12), time(15), time(16, 30), time(18), time(21), time(22)]
    yesterday = date(2026, 9, 7)
    now = datetime.combine(date(2026, 9, 8), time(9, 0))
    group = group_key("upwork", yesterday)
    subject = Subject(
        id="upwork",
        title="проверить upwork",
        cadence=Cadence.of(len(hours), "day"),
        window=Window(hours=hours),
    )
    widgets: list[Widget] = []
    instances: list[Instance] = []
    for index, hour in enumerate(hours):
        closed = index < 3
        when = datetime.combine(yesterday, hour)
        widgets.append(
            Widget(
                id=f"upwork-tick-{index}",
                type=WidgetType.tick,
                title="проверить upwork",
                payload=WidgetPayload(done=closed),
                status=WidgetStatus.done if closed else WidgetStatus.ready,
                when=when,
                section=WidgetSection.today,
                group_id=group,
                subject_id="upwork",
                instance_id=f"upwork-case-{index}",
                tile_size="2x2",
            )
        )
        instances.append(
            Instance(
                id=f"upwork-case-{index}",
                subject_id="upwork",
                when=when,
                status=InstanceStatus.completed if closed else InstanceStatus.prepared,
            )
        )

    projection = lid_projection(now, [subject], instances, widgets)
    # Nothing of yesterday is drawn — that is R19, and it stays true.
    assert not [item for item in projection.today if isinstance(item, WidgetTodayItem)]
    assert morning_delta(subject, instances, now) == len(hours)
    card = delta_card([subject], instances, widgets, now)
    assert card is not None
    assert card.subject_id == "upwork"
    assert card.remaining == len(hours)


def test_a_tile_standing_on_today_still_answers_for_it() -> None:
    """The other half of the same rule: a live tile of **today** is the delta."""
    hours = [time(10), time(12)]
    today = date(2026, 9, 8)
    now = datetime.combine(today, time(9, 0))
    group = group_key("upwork", today)
    subject = Subject(
        id="upwork",
        title="проверить upwork",
        cadence=Cadence.of(2, "day"),
        window=Window(hours=hours),
    )
    widgets = [
        Widget(
            id=f"upwork-tick-{index}",
            type=WidgetType.tick,
            title="проверить upwork",
            payload=WidgetPayload(done=False),
            status=WidgetStatus.ready,
            when=datetime.combine(today, hour),
            section=WidgetSection.today,
            group_id=group,
            subject_id="upwork",
            instance_id=f"upwork-case-{index}",
            tile_size="2x2",
        )
        for index, hour in enumerate(hours)
    ]
    instances = [
        Instance(
            id=f"upwork-case-{index}",
            subject_id="upwork",
            when=datetime.combine(today, hour),
            status=InstanceStatus.prepared,
        )
        for index, hour in enumerate(hours)
    ]
    # A closed case yesterday, so the practice has run at least once.
    instances.append(
        Instance(
            id="upwork-yesterday",
            subject_id="upwork",
            when=datetime.combine(date(2026, 9, 7), time(10)),
            status=InstanceStatus.completed,
        )
    )
    assert delta_card([subject], instances, widgets, now) is None
