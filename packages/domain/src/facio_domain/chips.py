"""Reply chips: the row above the composer (03 «Reply chips», Q35).

A chip **is text** — the sentence the person is about to say in their own name.
There is no id here, no action and no callback, because the moment a chip
carries one it stops being a shortcut through typing and becomes a button that
decides for the person ([06] never-do AI #2). Tapping one sends that text into
the same thread and the turn proceeds like any typed one.

Two things live here, and only these two:

* **the cap.** One to three, never a fourth: a row that grows into a menu is a
  form, and the composer stops being a conversation (03). One number, read from
  `weekdays.py` — that module caps its layouts by this same product rule, and
  two copies of a rule the PO can change is two places to forget.
* **the words a weekday is called by.** Q35's first real case asks which days a
  weekly promise sits on, and the answer has to be readable — «пн, ср, пт», not
  `[0, 2, 4]`. One table, both locales, so the names are never spelled out
  again somewhere else in Python.

What is deliberately **not** here: which days to pick. That is
`weekdays.layouts`, it is arithmetic over the count, and it stays locale-free —
days are ISO (Monday = 0), and the first day of the week changes only how a row
is *read*, which belongs to whoever draws it.
"""

from __future__ import annotations

from collections.abc import Sequence

from facio_domain.weekdays import MAX_LAYOUTS, layouts

# 03-product: «1–3, never a fourth». Defined next to the layouts because that
# module imports nothing; the rule belongs to the composer row and is the same
# number in both places, so it is read, never restated.
MAX_CHIPS = MAX_LAYOUTS
# The catalog's source language, used when a caller names a locale the table
# does not carry. The wire only ever offers `ru` / `en` (an unknown one is
# refused at the edge with 422), so this is a floor, not a translation policy.
DEFAULT_LOCALE = "ru"
WEEKDAY_NAMES: dict[str, tuple[str, ...]] = {
    "ru": ("пн", "вт", "ср", "чт", "пт", "сб", "вс"),
    "en": ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"),
}
SEPARATOR = ", "


def weekday_names(locale: str) -> tuple[str, ...]:
    """The seven names, ISO order, Monday first."""
    return WEEKDAY_NAMES.get(locale, WEEKDAY_NAMES[DEFAULT_LOCALE])


def weekday_chip(days: Sequence[int], locale: str) -> str:
    """One layout as the sentence a person would tap: «пн, ср, пт» / "Mon, Wed, Fri".

    Written in ISO order, because that is the order the layout came in and a row
    that reorders itself per locale would no longer be the same placement. Which
    day a week *starts* on is a reading question and lives on the client.
    """
    names = weekday_names(locale)
    return SEPARATOR.join(names[day] for day in days if 0 <= day < len(names))


def weekday_chips(count: int, locale: str, *, taken: Sequence[int] = ()) -> list[str]:
    """The day rows a `count`×/week promise may be offered, in the answer's language.

    Straight through `weekdays.layouts` — no second arithmetic, no second cap.
    A week that owes nothing, or has no room left for what it owes, offers an
    empty row: a chip that cannot be honoured is worse than no chip.
    """
    return [weekday_chip(days, locale) for days in layouts(count, taken=taken)]


def build_chips(raw: object) -> list[str] | None:
    """Read a chip row off a tool call, or refuse it by returning `None`.

    The caller names the refusal; this module does not raise product errors —
    the same split `runtime.build_checklist_items` uses.

    Refused, rather than repaired: an empty row (a call that offered nothing),
    a fourth chip, anything that is not plain text, and the same sentence
    twice — a row that draws one option and claims two. Trimming the ends of a
    string is not repair; filling in what the turn meant would be, and that is
    the silent rewrite AI #2 forbids.
    """
    if not isinstance(raw, list) or not raw:
        return None
    chips: list[str] = []
    for row in raw:
        if not isinstance(row, str):
            return None
        text = row.strip()
        if not text or text in chips:
            return None
        chips.append(text)
    if len(chips) > MAX_CHIPS:
        return None
    return chips
