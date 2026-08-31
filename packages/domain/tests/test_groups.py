"""One tile for the occurrences of one subject inside one period (Q34)."""

from __future__ import annotations

from datetime import date, datetime, time

from facio_domain.groups import (
    group_face,
    group_key,
    grouped_ids,
    is_closed,
    members,
    next_hour,
)
from facio_domain.models import (
    Instance,
    InstanceStatus,
    Widget,
    WidgetPayload,
    WidgetSection,
    WidgetStatus,
    WidgetType,
)
from facio_domain.slots import hour_instance_ids, occurrence_instances

DAY = date(2026, 8, 30)
HOURS = [time(10, 0), time(12, 0), time(15, 0), time(16, 30), time(18, 0), time(21, 0), time(22, 0)]
GROUP = group_key("upwork", DAY)


def _at(hour: time) -> datetime:
    return datetime.combine(DAY, hour)


def _check(index: int, *, done: bool = False, group: str | None = GROUP) -> Widget:
    hour = HOURS[index]
    return Widget(
        id=f"upwork-tick-{index}",
        type=WidgetType.tick,
        title="проверить upwork",
        payload=WidgetPayload(done=done),
        status=WidgetStatus.done if done else WidgetStatus.ready,
        when=_at(hour),
        section=WidgetSection.today,
        group_id=group,
        subject_id="upwork",
        instance_id=f"upwork-case-{index}",
        tile_size="2x2",
    )


def _case(index: int, *, status: InstanceStatus = InstanceStatus.prepared) -> Instance:
    return Instance(
        id=f"upwork-case-{index}",
        subject_id="upwork",
        when=_at(HOURS[index]),
        status=status,
    )


def _seven(done: set[int] = frozenset()) -> tuple[list[Widget], list[Instance]]:
    widgets = [_check(index, done=index in done) for index in range(len(HOURS))]
    cases = [_case(index) for index in range(len(HOURS))]
    return widgets, cases


def test_group_key_is_derived_not_invented() -> None:
    """Topping the same day up twice must re-stamp, never split."""
    assert group_key("upwork", DAY) == group_key("upwork", DAY)
    assert group_key("upwork", DAY) != group_key("upwork", date(2026, 8, 31))
    assert group_key("gym", DAY) != group_key("upwork", DAY)


def test_seven_checks_are_one_group() -> None:
    widgets, cases = _seven()
    assert grouped_ids(widgets) == [GROUP]
    assert len(members(GROUP, widgets)) == 7
    face = group_face(GROUP, widgets, cases, _at(time(9, 0)))
    assert face is not None
    assert face.total == 7
    assert face.done == 0
    assert [mark.hour for mark in face.marks] == HOURS


def test_a_widget_without_a_group_is_drawn_alone() -> None:
    """The old desk opens: no `group_id`, no group — one tile as before."""
    lone = _check(0, group=None)
    assert grouped_ids([lone]) == []
    assert group_face(GROUP, [lone], [_case(0)], _at(time(9, 0))) is None


def test_next_hour_is_the_nearest_one_still_ahead() -> None:
    widgets, cases = _seven()
    face = group_face(GROUP, widgets, cases, _at(time(15, 40)))
    assert face is not None
    assert face.next_hour == time(16, 30)


def test_a_later_check_does_not_close_an_earlier_miss() -> None:
    """The whole slice: marks are independent and unordered.

    Ticking 15:00 closes 15:00. The 12:00 that was missed stays open and stays
    visible — a pointer would have said «3 of 7» and lost which three.
    """
    widgets, cases = _seven(done={0, 2})
    face = group_face(GROUP, widgets, cases, _at(time(15, 40)))
    assert face is not None
    assert face.done == 2
    assert face.total == 7
    open_hours = [mark.hour for mark in face.marks if not mark.done]
    assert time(12, 0) in open_hours
    assert time(15, 0) not in open_hours
    # And the big hour has moved past the miss without swallowing it.
    assert face.next_hour == time(16, 30)


def test_when_every_hour_is_behind_the_first_open_one_is_shown() -> None:
    widgets, cases = _seven(done={0, 1})
    face = group_face(GROUP, widgets, cases, _at(time(23, 30)))
    assert face is not None
    assert face.next_hour == time(15, 0)


def test_a_finished_group_has_no_hour_left_to_show() -> None:
    widgets, cases = _seven(done=set(range(7)))
    face = group_face(GROUP, widgets, cases, _at(time(23, 30)))
    assert face is not None
    assert face.done == 7
    assert face.next_hour is None


def test_skipped_is_not_done() -> None:
    """A check that did not happen must not be drawn struck off."""
    widget = _check(1).model_copy(update={"status": WidgetStatus.skipped})
    assert is_closed(widget) is False


def test_a_ticked_payload_counts_even_before_the_status_moves() -> None:
    widget = _check(1).model_copy(
        update={"status": WidgetStatus.ready, "payload": WidgetPayload(done=True)}
    )
    assert is_closed(widget) is True


def test_marks_are_ordered_by_hour_whatever_order_they_arrive_in() -> None:
    widgets, cases = _seven()
    shuffled = [widgets[4], widgets[0], widgets[6], widgets[2], widgets[1], widgets[5], widgets[3]]
    face = group_face(GROUP, shuffled, cases, _at(time(9, 0)))
    assert face is not None
    assert [mark.hour for mark in face.marks] == HOURS


def test_next_hour_of_nothing_is_nothing() -> None:
    assert next_hour([], datetime.combine(DAY, time(9, 0))) is None


# --- the reminder is an hour, not an occurrence (Part B) -------------------


def _alarm() -> tuple[Widget, Instance]:
    case = Instance(
        id="upwork-open",
        subject_id="upwork",
        when=_at(HOURS[0]),
        status=InstanceStatus.prepared,
    )
    widget = Widget(
        id="upwork-reminder",
        type=WidgetType.reminder,
        title="проверить upwork",
        payload=WidgetPayload(fire_at=_at(HOURS[0])),
        status=WidgetStatus.ready,
        when=_at(HOURS[0]),
        section=WidgetSection.today,
        subject_id="upwork",
        instance_id=case.id,
        tile_size="4x2",
    )
    return widget, case


def test_the_reminder_case_is_not_a_slot_of_the_carousel() -> None:
    widgets, cases = _seven()
    alarm, alarm_case = _alarm()
    listed = occurrence_instances("upwork", [alarm_case, *cases], [alarm, *widgets])
    assert hour_instance_ids("upwork", [alarm, *widgets]) == {"upwork-open"}
    assert [case.id for case in listed] == [case.id for case in cases]


def test_a_practice_whose_only_case_is_its_alarm_keeps_it() -> None:
    """The bike: the alarm is the ride, and an empty carousel is worse."""
    alarm, alarm_case = _alarm()
    listed = occurrence_instances("upwork", [alarm_case], [alarm])
    assert [case.id for case in listed] == ["upwork-open"]
