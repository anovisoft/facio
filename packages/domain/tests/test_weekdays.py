from __future__ import annotations

import pytest

from facio_domain.weekdays import layouts

MON, TUE, WED, THU, FRI, SAT, SUN = range(7)


def test_three_a_week_offers_the_three_the_po_named() -> None:
    # «пн, вт, ср» / «пн, ср, пт» / «пн, чт, вс» — the tight run, the spread
    # over the working days, the spread over the whole week.
    assert layouts(3) == [[MON, TUE, WED], [MON, WED, FRI], [MON, THU, SUN]]


def test_never_more_than_three_options() -> None:
    for count in range(1, 8):
        assert len(layouts(count)) <= 3, count


def test_identical_shapes_collapse_instead_of_padding_the_row() -> None:
    # Five over five working days is the run, the working spread and — once the
    # week spread rounds — three ways of saying Monday to Friday is one option.
    assert layouts(5)[0] == [MON, TUE, WED, THU, FRI]
    assert all(len(row) == 5 for row in layouts(5))
    assert len(layouts(5)) == len({tuple(row) for row in layouts(5)})


def test_every_option_carries_exactly_the_count() -> None:
    for count in range(1, 8):
        for row in layouts(count):
            assert len(row) == count, (count, row)
            assert row == sorted(set(row)), row


def test_days_already_spent_keep_what_they_hold() -> None:
    # Two of the three already sat this week: only the third is placed, and
    # never on a day that already holds one.
    rows = layouts(3, taken=[MON, WED])
    assert rows, "one is still owed and there is room for it"
    for row in rows:
        assert len(row) == 1
        assert MON not in row and WED not in row


def test_a_week_that_owes_nothing_offers_nothing() -> None:
    # Silence is the right answer: there is nothing left to ask about, and a
    # chip that cannot be honoured is worse than no chip.
    assert layouts(2, taken=[TUE, FRI]) == []
    assert layouts(1, taken=[SUN]) == []


def test_a_week_with_no_room_left_offers_nothing() -> None:
    assert layouts(3, taken=[MON, TUE, WED, THU, FRI, SAT]) == []


def test_a_count_a_week_cannot_hold_is_not_offered() -> None:
    assert layouts(8) == []
    assert layouts(0) == []
    assert layouts(-1) == []


def test_seven_a_week_is_the_whole_week_once() -> None:
    assert layouts(7) == [[MON, TUE, WED, THU, FRI, SAT, SUN]]


@pytest.mark.parametrize("count", range(1, 8))
def test_two_calls_on_one_week_answer_the_same(count: int) -> None:
    assert layouts(count) == layouts(count)


def test_nothing_offered_outside_the_week() -> None:
    for count in range(1, 8):
        for row in layouts(count):
            assert all(0 <= day < 7 for day in row), row
