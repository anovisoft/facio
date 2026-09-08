from __future__ import annotations

from datetime import datetime, time

from facio_domain.fixtures import instances_from_rows
from facio_domain.groups import group_key
from facio_domain.lid import lid_projection
from facio_domain.models import (
    Cadence,
    DeltaTodayItem,
    DriftTodayItem,
    Instance,
    InstanceStatus,
    RankBand,
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
from facio_domain.reminder import reminder_fire_times


def _widget(
    widget_id: str,
    *,
    status: WidgetStatus = WidgetStatus.ready,
    when: datetime | None = None,
    section: WidgetSection = WidgetSection.today,
    subject_id: str = "push-ups",
) -> Widget:
    return Widget(
        id=widget_id,
        type=WidgetType.counter,
        title=widget_id,
        payload=WidgetPayload(),
        status=status,
        when=when,
        section=section,
        subject_id=subject_id,
        instance_id=f"{widget_id}-inst",
        version=1,
    )


def test_empty_today_without_commitments_stays_empty(
    subjects, scenarios, now
) -> None:
    case = scenarios["empty_today_no_commitments"]
    projection = lid_projection(
        now, subjects, instances_from_rows(case["instances"]), []
    )
    assert projection.today == []
    assert projection.drift_card is None
    assert projection.delta_card is None


def test_empty_today_with_drift_shows_one_card(subjects, scenarios, now) -> None:
    case = scenarios["empty_today_with_drift"]
    projection = lid_projection(
        now, subjects, instances_from_rows(case["instances"]), []
    )
    assert projection.drift_card is not None
    assert projection.drift_card.subject_id == "bike"
    assert len(projection.today) == 1
    item = projection.today[0]
    assert isinstance(item, DriftTodayItem)
    assert item.kind == "drift"
    assert item.band == RankBand.drift_card


def test_done_widget_today_stays_in_today(subjects, now) -> None:
    widgets = [_widget("done-set", status=WidgetStatus.done, when=now)]
    projection = lid_projection(now, subjects, [], widgets)
    assert len(projection.today) == 1
    item = projection.today[0]
    assert isinstance(item, WidgetTodayItem)
    assert item.widget.id == "done-set"
    assert item.band == RankBand.today_done


def test_done_widget_other_day_leaves_today(subjects, now) -> None:
    yesterday = datetime(2026, 8, 14, 12, 0, 0)
    widgets = [_widget("old-set", status=WidgetStatus.done, when=yesterday)]
    projection = lid_projection(now, subjects, [], widgets)
    assert projection.today == []


def test_lifetime_done_today_returns_to_today(subjects, now) -> None:
    widgets = [
        _widget(
            "push-done",
            status=WidgetStatus.done,
            when=now,
            section=WidgetSection.lifetime,
        )
    ]
    projection = lid_projection(now, subjects, [], widgets)
    assert len(projection.today) == 1
    item = projection.today[0]
    assert isinstance(item, WidgetTodayItem)
    assert item.band == RankBand.today_done
    assert item.widget.id == "push-done"
    assert projection.lifetime == []


def test_lifetime_done_other_day_leaves_lid(subjects, now) -> None:
    yesterday = datetime(2026, 8, 14, 12, 0, 0)
    widgets = [
        _widget(
            "old-set",
            status=WidgetStatus.done,
            when=yesterday,
            section=WidgetSection.lifetime,
        )
    ]
    projection = lid_projection(now, subjects, [], widgets)
    assert projection.today == []
    assert projection.lifetime == []


def test_rank_v0_order(subjects, now) -> None:
    running = _widget("running", status=WidgetStatus.running, when=now)
    overdue = _widget("overdue", when=datetime(2026, 8, 15, 8, 0, 0))
    later = _widget("later", when=datetime(2026, 8, 15, 18, 0, 0))
    incomplete = _widget("incomplete")
    done = _widget("done-set", status=WidgetStatus.done, when=now)
    projection = lid_projection(
        now, subjects, [], [later, incomplete, overdue, running, done]
    )
    ids = [
        item.widget.id
        for item in projection.today
        if isinstance(item, WidgetTodayItem)
    ]
    assert ids == ["running", "overdue", "later", "incomplete", "done-set"]
    bands = [
        item.band for item in projection.today if isinstance(item, WidgetTodayItem)
    ]
    assert bands == [
        RankBand.in_progress,
        RankBand.overdue,
        RankBand.soon_by_time,
        RankBand.today_incomplete,
        RankBand.today_done,
    ]


def test_drift_card_ranks_between_overdue_and_soon(
    subjects, scenarios, now
) -> None:
    case = scenarios["empty_today_with_drift"]
    overdue = _widget("overdue", when=datetime(2026, 8, 15, 8, 0, 0))
    later = _widget("later", when=datetime(2026, 8, 15, 18, 0, 0))
    projection = lid_projection(
        now, subjects, instances_from_rows(case["instances"]), [later, overdue]
    )
    kinds = [item.kind for item in projection.today]
    assert kinds == ["widget", "drift", "widget"]
    assert isinstance(projection.today[0], WidgetTodayItem)
    assert projection.today[0].widget.id == "overdue"
    assert isinstance(projection.today[1], DriftTodayItem)
    assert isinstance(projection.today[2], WidgetTodayItem)
    assert projection.today[2].widget.id == "later"


def test_done_today_ranks_after_live_and_drift(
    subjects, scenarios, now
) -> None:
    case = scenarios["empty_today_with_drift"]
    live = _widget("live")
    done = _widget("done-set", status=WidgetStatus.done, when=now)
    projection = lid_projection(
        now, subjects, instances_from_rows(case["instances"]), [live, done]
    )
    kinds = [item.kind for item in projection.today]
    assert kinds == ["drift", "widget", "widget"]
    assert isinstance(projection.today[1], WidgetTodayItem)
    assert projection.today[1].band == RankBand.today_incomplete
    assert isinstance(projection.today[2], WidgetTodayItem)
    assert projection.today[2].band == RankBand.today_done


def test_no_invented_morning_card(subjects, now) -> None:
    projection = lid_projection(now, subjects, [], [_widget("only")])
    assert all(
        not (isinstance(item, WidgetTodayItem) and item.band == RankBand.unanswered_morning)
        for item in projection.today
    )
    assert projection.delta_card is None


def test_delta_card_ranks_above_the_drift_slot(subjects, scenarios, now) -> None:
    """Rank v0: unanswered morning sits between overdue and the drift slot."""
    case = scenarios["empty_today_with_delta"]
    # Tiles of another practice: a subject already sitting on Today does not
    # need the morning to repeat its own tile back at it.
    overdue = _widget(
        "overdue", when=datetime(2026, 8, 15, 8, 0, 0), subject_id="vegetables"
    )
    later = _widget(
        "later", when=datetime(2026, 8, 15, 18, 0, 0), subject_id="vegetables"
    )
    projection = lid_projection(
        now,
        subjects,
        instances_from_rows(case["instances"]),
        [later, overdue],
    )
    assert [item.kind for item in projection.today] == ["widget", "delta", "widget"]
    item = projection.today[1]
    assert isinstance(item, DeltaTodayItem)
    assert item.band == RankBand.unanswered_morning


def test_sections_pass_through(subjects, widgets, now) -> None:
    projection = lid_projection(now, subjects, [], widgets)
    assert {item.id for item in projection.lifetime} == {
        "push-ups-counter",
        "bike-reminder",
        "vegetables-tick",
    }
    assert projection.today == []
    assert projection.soon == []
    assert projection.postponed == []


def test_paused_bike_reminder_leaves_all_sections(subjects, widgets, now) -> None:
    paused = [
        subject.model_copy(update={"status": SubjectStatus.paused, "paused_at": now})
        if subject.id == "bike"
        else subject
        for subject in subjects
    ]
    today_bike = next(row for row in widgets if row.id == "bike-reminder").model_copy(
        update={"section": WidgetSection.today}
    )
    projection = lid_projection(now, paused, [], [*widgets, today_bike])
    today_ids = {
        item.widget.id
        for item in projection.today
        if isinstance(item, WidgetTodayItem)
    }
    section_ids = {
        widget.id
        for widget in [*projection.lifetime, *projection.soon, *projection.postponed]
    }
    assert "bike-reminder" not in today_ids
    assert "bike-reminder" not in section_ids
    assert "push-ups-counter" in section_ids


# --- R17: one practice, one card -------------------------------------------
#
# The phone showed one subject wearing two tiles that said the same thing: the
# reminder («15:30» large, «18:00 22:00» small) and the group of the same day
# («0/3», «15:30», the row of marks). The lid is a view of what is due now, not
# a second inventory (P10), so the reminder is not drawn — and it is not
# touched: it stays on the desk and keeps ringing.

UPWORK_HOURS = [time(15, 30), time(18, 0), time(22, 0)]
UPWORK_DAY = datetime(2026, 8, 15, 9, 0, 0)
UPWORK_GROUP = group_key("upwork", UPWORK_DAY.date())


def _upwork(
    *,
    hours: list[time] | None = None,
    laid: list[time] | None = None,
    group: str | None = UPWORK_GROUP,
    checks: int = 3,
) -> tuple[Subject, list[Instance], list[Widget]]:
    """A practice promising `checks` a day, with a reminder standing beside it.

    `hours` is what the person said (the window); `laid` is what actually landed
    on the cases. They differ exactly when R16 refused to guess which check
    happens when.
    """
    stated = UPWORK_HOURS if hours is None else hours
    on_cases = stated if laid is None else laid
    subject = Subject(
        id="upwork",
        title="посмотреть Upwork",
        cadence=Cadence.of(checks, "day"),
        window=Window(hours=list(stated)),
    )
    cases = [
        Instance(
            id=f"upwork-case-{index}",
            subject_id="upwork",
            when=datetime.combine(UPWORK_DAY.date(), on_cases[index % len(on_cases)]),
            status=InstanceStatus.prepared,
        )
        for index in range(checks)
    ]
    ticks = [
        Widget(
            id=f"upwork-tick-{index}",
            type=WidgetType.tick,
            title="посмотреть Upwork",
            payload=WidgetPayload(done=False),
            status=WidgetStatus.ready,
            when=case.when,
            section=WidgetSection.today,
            group_id=group,
            subject_id="upwork",
            instance_id=case.id,
        )
        for index, case in enumerate(cases)
    ]
    alarm = Widget(
        id="upwork-reminder",
        type=WidgetType.reminder,
        title="посмотреть Upwork",
        payload=WidgetPayload(fire_at=datetime.combine(UPWORK_DAY.date(), stated[0])),
        status=WidgetStatus.ready,
        when=datetime.combine(UPWORK_DAY.date(), stated[0]),
        section=WidgetSection.today,
        subject_id="upwork",
        instance_id="upwork-hour",
    )
    hour_case = Instance(
        id="upwork-hour",
        subject_id="upwork",
        when=alarm.when,
        status=InstanceStatus.prepared,
    )
    return subject, [*cases, hour_case], [*ticks, alarm]


def _today_ids(projection) -> list[str]:
    return [
        item.widget.id
        for item in projection.today
        if isinstance(item, WidgetTodayItem)
    ]


def test_group_with_the_hours_hides_the_reminder_tile() -> None:
    subject, cases, widgets = _upwork()
    projection = lid_projection(UPWORK_DAY, [subject], cases, widgets)
    assert "upwork-reminder" not in _today_ids(projection)
    assert _today_ids(projection) == [
        "upwork-tick-0",
        "upwork-tick-1",
        "upwork-tick-2",
    ]


def test_the_hidden_reminder_is_gone_from_every_section() -> None:
    subject, cases, widgets = _upwork()
    for section in WidgetSection:
        moved = [
            widget.model_copy(update={"section": section})
            if widget.id == "upwork-reminder"
            else widget
            for widget in widgets
        ]
        projection = lid_projection(UPWORK_DAY, [subject], cases, moved)
        drawn = {
            *_today_ids(projection),
            *(widget.id for widget in projection.lifetime),
            *(widget.id for widget in projection.soon),
            *(widget.id for widget in projection.postponed),
        }
        assert "upwork-reminder" not in drawn, section


def test_hiding_the_tile_does_not_touch_the_desk() -> None:
    """The projection is a view. The widget it did not draw is still there."""
    subject, cases, widgets = _upwork()
    before = [widget.model_copy(deep=True) for widget in widgets]
    lid_projection(UPWORK_DAY, [subject], cases, widgets)
    assert widgets == before
    alarm = next(widget for widget in widgets if widget.id == "upwork-reminder")
    assert alarm.status == WidgetStatus.ready
    assert alarm.status != WidgetStatus.archived


def test_the_alarms_are_the_same_with_the_tile_hidden() -> None:
    """`ReminderScheduler` reads the desk, not this projection (mirror lock)."""
    subject, cases, widgets = _upwork()
    assert subject.window is not None
    before = reminder_fire_times(subject.window, UPWORK_DAY.date())
    projection = lid_projection(UPWORK_DAY, [subject], cases, widgets)
    after = reminder_fire_times(subject.window, UPWORK_DAY.date())
    assert "upwork-reminder" not in _today_ids(projection)
    assert after == before
    assert len(after) == 3
    assert [moment.time() for moment in after] == UPWORK_HOURS


def test_a_practice_without_a_group_draws_its_reminder(subjects, widgets, now) -> None:
    """The bike: one hour, no group. Nothing about it changes."""
    today_bike = next(row for row in widgets if row.id == "bike-reminder").model_copy(
        update={"section": WidgetSection.today}
    )
    projection = lid_projection(now, subjects, [], [today_bike])
    assert _today_ids(projection) == ["bike-reminder"]


def test_fewer_hours_than_checks_keeps_the_reminder() -> None:
    """R16 refuses to guess which check is when — so the hours live on the
    reminder alone, and killing it would cost the person the hours."""
    subject, cases, widgets = _upwork(laid=[time(9, 0)], checks=3)
    projection = lid_projection(UPWORK_DAY, [subject], cases, widgets)
    assert "upwork-reminder" in _today_ids(projection)


def test_a_group_of_one_keeps_the_reminder() -> None:
    subject, cases, widgets = _upwork(hours=[time(15, 30)], checks=1)
    projection = lid_projection(UPWORK_DAY, [subject], cases, widgets)
    assert "upwork-reminder" in _today_ids(projection)


def test_an_ungrouped_desk_keeps_the_reminder() -> None:
    """Every widget on a desk written before Q34 carries no `group_id`."""
    subject, cases, widgets = _upwork(group=None)
    projection = lid_projection(UPWORK_DAY, [subject], cases, widgets)
    assert "upwork-reminder" in _today_ids(projection)


def test_yesterdays_group_does_not_hide_todays_reminder() -> None:
    subject, cases, widgets = _upwork(
        group=group_key("upwork", datetime(2026, 8, 14, 9, 0, 0).date())
    )
    projection = lid_projection(UPWORK_DAY, [subject], cases, widgets)
    assert "upwork-reminder" in _today_ids(projection)


def test_a_practice_without_a_window_keeps_its_reminder() -> None:
    subject, cases, widgets = _upwork()
    windowless = subject.model_copy(update={"window": None})
    projection = lid_projection(UPWORK_DAY, [windowless], cases, widgets)
    assert "upwork-reminder" in _today_ids(projection)


def test_a_paused_practice_is_still_silent() -> None:
    """The old lock: paused says nothing at all, group or no group."""
    subject, cases, widgets = _upwork()
    paused = subject.model_copy(
        update={"status": SubjectStatus.paused, "paused_at": UPWORK_DAY}
    )
    projection = lid_projection(UPWORK_DAY, [paused], cases, widgets)
    assert _today_ids(projection) == []


def test_an_archived_reminder_is_not_resurrected_by_the_rule() -> None:
    subject, cases, widgets = _upwork()
    archived = [
        widget.model_copy(update={"status": WidgetStatus.archived})
        if widget.id == "upwork-reminder"
        else widget
        for widget in widgets
    ]
    projection = lid_projection(UPWORK_DAY, [subject], cases, archived)
    assert "upwork-reminder" not in _today_ids(projection)


def test_a_closed_group_still_hides_the_reminder() -> None:
    """3/3 done is still one practice: the day is answered, not re-asked."""
    subject, cases, widgets = _upwork()
    closed = [
        widget.model_copy(
            update={"status": WidgetStatus.done, "payload": WidgetPayload(done=True)}
        )
        if widget.type == WidgetType.tick
        else widget
        for widget in widgets
    ]
    projection = lid_projection(UPWORK_DAY, [subject], cases, closed)
    assert "upwork-reminder" not in _today_ids(projection)
