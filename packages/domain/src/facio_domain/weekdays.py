"""Which weekdays a weekly promise sits on (Q35, first real case of Q26).

`3×/week` says **how many**, never which days, and that does not change: a
cadence is a count per period, and fixed weekdays as a cadence stay a trap
([06] never-do). Somebody still has to put three occurrences into seven days,
and the law must not: choosing days for a person is the desk deciding in
silence what they committed to (AI #2). So the assistant offers, the person
picks, and this module is what it is allowed to offer.

**These are layouts of the count, not lucky days.** Nothing here knows that
Monday is a fresh start or that Friday is hard. Each option is a different
*spacing* of the same promise across the same week — the tight run, the spread
over the working days, the spread over the whole week — which is exactly the
three the PO named: «пн, вт, ср» / «пн, ср, пт» / «пн, чт, вс».

A chosen day is a **placement, not a per-day promise**: missing Wednesday is
not a failure, missing the count is. The same relation Q34 struck between the
hours of a window and the occurrences of a day.

Days are ISO, Monday = 0 … Sunday = 6, the same numbering `slots.py` uses. The
name of a weekday and which day a week starts on belong to whoever draws the
chip, not here.
"""

from __future__ import annotations

from collections.abc import Sequence

DAYS_IN_WEEK = 7
# Monday…Friday. Used for one of the three spacings — «every other weekday» is
# a shape people actually name — and for nothing else. It is not a claim about
# when anybody works.
WORKING_DAYS = 5
# 03-product: one to three, never a fourth. A row that grows into a menu is a
# form, and the composer stops being a conversation.
#
# It is a rule about the **row above the composer**, not about spacing — a week
# could be laid out five ways — and it is defined here only because this module
# imports nothing and `chips.py` imports this one. `chips.MAX_CHIPS` reads it
# from here: the day PO says four, one number moves.
MAX_LAYOUTS = 3


def _spread(days: Sequence[int], count: int) -> list[int]:
    """`count` days taken from `days`, as far apart as the run allows.

    Both ends are always used, and the rest land on the even divisions between
    them — one day is the first, two are the ends, three are the ends and the
    middle. Rounding can land twice on the same day in a short run; the result
    is de-duplicated and comes back shorter, and the caller drops it rather
    than padding, because a padded spread is no longer the spacing it claims.
    """
    if count <= 0 or not days:
        return []
    if count == 1:
        return [days[0]]
    if count >= len(days):
        return list(days)
    step = (len(days) - 1) / (count - 1)
    picked: list[int] = []
    for index in range(count):
        day = days[round(index * step)]
        if day not in picked:
            picked.append(day)
    return sorted(picked)


def layouts(count: int, *, taken: Sequence[int] = ()) -> list[list[int]]:
    """Up to three ways to lay `count` occurrences over one week.

    `taken` is the days of this week that already hold an occurrence — done or
    still standing. They keep what they hold: the layouts place only what is
    still owed, and only on days that are still free. A week that already owes
    nothing, or has no room left for what it owes, offers nothing at all —
    silence is the correct answer there, and a chip that cannot be honoured is
    worse than no chip.

    The three shapes, in the order a person reads them:

    * the **tight run** — the owed days back to back, starting from the first
      free one;
    * the **working-week spread** — the same count spread across Monday to
      Friday;
    * the **week spread** — spread across all seven.

    Identical results collapse (a count of 5 spreads the same way twice), and
    what is left is capped at three. Two calls on the same week return the same
    list in the same order: nothing here reads a clock or a random seed, so a
    chip row can be replayed in a test.
    """
    if count <= 0 or count > DAYS_IN_WEEK:
        return []
    spent = {day for day in taken if 0 <= day < DAYS_IN_WEEK}
    owed = count - len(spent)
    free = [day for day in range(DAYS_IN_WEEK) if day not in spent]
    if owed <= 0 or owed > len(free):
        return []

    candidates = [
        free[:owed],
        _spread([day for day in free if day < WORKING_DAYS], owed),
        _spread(free, owed),
    ]
    offered: list[list[int]] = []
    for option in candidates:
        if len(option) != owed:
            continue
        row = sorted(option)
        if row not in offered:
            offered.append(row)
    return offered[:MAX_LAYOUTS]
