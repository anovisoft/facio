from __future__ import annotations

from datetime import datetime

from facio_domain.chips import MAX_CHIPS, build_chips, weekday_chip, weekday_chips
from facio_domain.desk import founding_desk
from facio_domain.models import CueOrigin
from facio_domain.tools import INVALID_CHIPS, TOOL_NAMES, apply_tool

NOW = datetime(2026, 8, 15, 12, 0, 0)
ORIGIN = CueOrigin(chat_id="chat-1", message_id="msg-1")
MON, TUE, WED, THU, FRI, SAT, SUN = range(7)


def _apply(desk, arguments: dict):
    return apply_tool(desk, "offer_chips", arguments, pain=False, now=NOW, origin=ORIGIN)


def test_the_even_spread_is_read_out_in_both_languages() -> None:
    # The row the PO wrote down, and the one the whole naming exists for. If
    # this string ever drifts, the chip stops being the sentence the person
    # would have typed.
    assert weekday_chip([MON, WED, FRI], "ru") == "пн, ср, пт"
    assert weekday_chip([MON, WED, FRI], "en") == "Mon, Wed, Fri"


def test_three_a_week_reads_as_the_three_rows_the_po_named() -> None:
    assert weekday_chips(3, "ru") == ["пн, вт, ср", "пн, ср, пт", "пн, чт, вс"]
    assert weekday_chips(3, "en") == ["Mon, Tue, Wed", "Mon, Wed, Fri", "Mon, Thu, Sun"]


def test_the_row_is_written_in_iso_order_in_either_language() -> None:
    # The first day of the week changes how a row is *read*, not which days it
    # holds — that reading belongs to the client (Q35). Both languages name the
    # same placement in the same order.
    assert weekday_chip([SAT, SUN], "ru") == "сб, вс"
    assert weekday_chip([SAT, SUN], "en") == "Sat, Sun"


def test_a_week_with_no_room_offers_no_row() -> None:
    # A chip that cannot be honoured is worse than no chip: `weekdays.layouts`
    # already says so, and the naming does not invent a row it was not given.
    assert weekday_chips(3, "ru", taken=[MON, TUE, WED]) == []
    assert weekday_chips(0, "en") == []


def test_a_row_never_grows_past_three() -> None:
    for count in range(1, 8):
        assert len(weekday_chips(count, "ru")) <= MAX_CHIPS, count


def test_offer_chips_leaves_the_desk_byte_for_byte_alone() -> None:
    # A chip is an offer. Nothing moved, so `mutated` stays down and there is
    # no snapshot card to write — a card would claim the desk changed.
    desk = founding_desk(now=NOW)
    before = desk.model_copy(deep=True)
    outcome = _apply(desk, {"chips": ["Напомни завтра"]})
    assert outcome.ok
    assert outcome.mutated is False
    assert outcome.snapshot_widget_ids == []
    assert outcome.data == {"chips": ["Напомни завтра"]}
    assert outcome.desk == before


def test_one_chip_is_a_row_and_three_are_a_row() -> None:
    desk = founding_desk(now=NOW)
    row = ["пн, вт, ср", "пн, ср, пт", "пн, чт, вс"]
    assert _apply(desk, {"chips": row}).data == {"chips": row}
    assert _apply(desk, {"chips": row[:1]}).data == {"chips": row[:1]}


def test_an_empty_row_and_a_fourth_chip_are_both_refused_by_name() -> None:
    desk = founding_desk(now=NOW)
    for arguments in ({}, {"chips": []}, {"chips": ["a", "b", "c", "d"]}):
        outcome = _apply(desk, arguments)
        assert not outcome.ok, arguments
        assert outcome.error == INVALID_CHIPS, arguments


def test_a_chip_that_is_not_a_sentence_is_refused_rather_than_repaired() -> None:
    # An id, an action, a callback — the shapes that would turn a chip into a
    # button — come back named instead of being unwrapped into their text
    # (never-do AI #2). So do a blank chip and the same sentence twice.
    desk = founding_desk(now=NOW)
    for chips in (
        [{"id": "tomorrow", "text": "Напомни завтра"}],
        ["Напомни завтра", "   "],
        ["Напомни завтра", "Напомни завтра"],
        "Напомни завтра",
    ):
        outcome = _apply(desk, {"chips": chips})
        assert not outcome.ok, chips
        assert outcome.error == INVALID_CHIPS, chips


def test_build_chips_trims_the_ends_and_keeps_the_words() -> None:
    assert build_chips(["  Напомни завтра  "]) == ["Напомни завтра"]
    assert build_chips(["Remind me tomorrow", "Skip today"]) == [
        "Remind me tomorrow",
        "Skip today",
    ]


def test_offer_chips_is_the_last_name_in_the_block() -> None:
    # The schemas render ahead of the system prompt and the vendors cache on
    # that prefix: a new name goes on the end or every cached turn before it
    # stops being cached.
    assert TOOL_NAMES[-1] == "offer_chips"
