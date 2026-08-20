from __future__ import annotations

from datetime import datetime

from facio_domain.fixtures import instances_from_rows
from facio_domain.lid import lid_projection
from facio_domain.models import (
    DriftTodayItem,
    RankBand,
    SubjectStatus,
    Widget,
    WidgetPayload,
    WidgetSection,
    WidgetStatus,
    WidgetTodayItem,
    WidgetType,
)


def _widget(
    widget_id: str,
    *,
    status: WidgetStatus = WidgetStatus.ready,
    when: datetime | None = None,
    section: WidgetSection = WidgetSection.today,
) -> Widget:
    return Widget(
        id=widget_id,
        type=WidgetType.counter,
        title=widget_id,
        payload=WidgetPayload(),
        status=status,
        when=when,
        section=section,
        subject_id="push-ups",
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
