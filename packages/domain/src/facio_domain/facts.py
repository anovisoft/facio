"""Retrieval over the person's own facts (В3.3). Their cues, nothing else.

«Поясница уже была» — the mouth has to be able to find a line the person once
said about a practice it is not currently looking at, when `get_subject` is not
enough. What it reads is the desk: cues, which are already facts bound to a
subject and to a place they appear ([05](../../../../docs/rfc/05-ai-and-memory.md)
Memory). Not the transcript — a raw chat dump in an index is never-do AI #3 —
and never a catalogue of exercises or anything off the internet (never-do #23).
There is no corpus to build here, and nothing crosses the border of one desk.

**No embeddings and no new dependency.** One person's cues are a few dozen lines
they wrote themselves, so word overlap answers the question, while a vector
model costs money on every turn and gives a different order on two runs of the
same desk — a golden could not be replayed against it. The ranking is
arithmetic anyone can read straight off the answer: how many of the asked words
are in the line itself, then how many are in the name of the practice, then how
recently that practice actually happened.

**Reading changes nothing.** A search is not permission to write and not an
answer to the drift ladder: whatever it finds, a conclusion still lands through
`add_cue` and a number still moves only through the tool that moves it.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from datetime import datetime
from typing import NamedTuple

from pydantic import BaseModel, ConfigDict

from facio_domain.models import Cue, CueSurface, Instance, Subject

# Five is what one short answer can carry. The mouth speaks in a sentence or
# two; a list longer than this is either read back as a lecture or silently
# dropped, and both are worse than the best five.
MAX_FACTS = 5
# The stem two words have to share to count as one word. Russian inflects, so
# «поясницей» would never find «поясницу» by equality.
STEM = 4
# Below this, a shared prefix is a coincidence: «он» and «она», «run» and «rug».
MIN_SHARED = 3
# A single letter is never a fact.
MIN_WORD = 2

# Words every sentence has, in both languages the product ships in. They are
# dropped from the query so «что там было про поясницу» searches for
# «поясницу» — otherwise «что» matches a line that merely contains «что» and
# the ranking is decided by grammar instead of by the fact. Only function
# words: a verb the person chose is a word they meant.
STOP_WORDS = frozenset(
    {
        "а",
        "бы",
        "был",
        "была",
        "было",
        "были",
        "в",
        "во",
        "вы",
        "где",
        "да",
        "для",
        "до",
        "еще",
        "ещё",
        "же",
        "за",
        "и",
        "из",
        "или",
        "к",
        "как",
        "ко",
        "когда",
        "ли",
        "меня",
        "мне",
        "мной",
        "мои",
        "мой",
        "моя",
        "моё",
        "мы",
        "на",
        "над",
        "не",
        "но",
        "о",
        "об",
        "он",
        "она",
        "они",
        "оно",
        "от",
        "по",
        "под",
        "при",
        "про",
        "с",
        "со",
        "так",
        "там",
        "то",
        "тот",
        "ты",
        "у",
        "уже",
        "чем",
        "что",
        "эта",
        "эти",
        "это",
        "этот",
        "я",
        "a",
        "about",
        "again",
        "already",
        "an",
        "and",
        "any",
        "are",
        "as",
        "at",
        "be",
        "been",
        "but",
        "by",
        "did",
        "do",
        "does",
        "down",
        "for",
        "from",
        "had",
        "has",
        "have",
        "how",
        "i",
        "in",
        "is",
        "it",
        "me",
        "my",
        "of",
        "on",
        "or",
        "our",
        "that",
        "the",
        "their",
        "then",
        "there",
        "this",
        "to",
        "was",
        "we",
        "were",
        "what",
        "when",
        "where",
        "with",
        "you",
        "your",
    }
)

# Letters and digits, any alphabet: «зал до 22» keeps the 22, «push-ups» is two
# words and matches a query that says either half.
_WORD = re.compile(r"[^\W_]+", re.UNICODE)


class Fact(BaseModel):
    """One fact the search found — the person's own line and where it lives.

    Every field is already on the desk: the cue it came from, the practice it
    is bound to, the surface that says where it is seen, and the last time that
    practice actually happened — which is **not** the day the line was written,
    because a cue has no such day and none is invented here.

    Nothing is generated. A fact the search itself wrote would be the invented
    advice never-do AI #1 forbids, wearing a quotation mark.
    """

    model_config = ConfigDict(extra="forbid")

    cue_id: str
    subject_id: str
    text: str
    surface: CueSurface
    # Named for what it is. A cue carries no stamp of its own (04), so this is
    # the newest case of the practice the fact is bound to — and the name has
    # to say so, or a turn reads it as «you said this on the 20th» and tells
    # the person a date they never gave. It is also the tie-break key, so the
    # answer shows the number it was ranked by.
    practice_last_done: datetime | None = None


class _Ranked(NamedTuple):
    """One candidate with the numbers it was ranked by. Internal on purpose:
    the answer carries the fact, not our arithmetic about it."""

    text_hits: int
    title_hits: int
    when: datetime | None
    position: int
    fact: Fact


def words(text: str) -> list[str]:
    """The words of a line, folded. Order and repeats kept."""
    return [row.casefold() for row in _WORD.findall(text)]


def query_words(query: str) -> list[str]:
    """What the person actually asked about: their words, minus the ones every
    sentence has, each counted once.

    A query left with nothing after this is not an error — it is a query that
    names no fact, and the search answers it with no facts.
    """
    asked: list[str] = []
    for word in words(query):
        if len(word) < MIN_WORD or word in STOP_WORDS:
            continue
        if word not in asked:
            asked.append(word)
    return asked


def same_word(left: str, right: str) -> bool:
    """Whether two words are the same fact.

    Equality alone would find nothing in Russian: «поясницей» and «поясницу»
    are one word to the person and two to `==`. So words count as one when they
    share a stem — the first `STEM` characters, or the whole of the shorter word
    when it is shorter than that, and never fewer than `MIN_SHARED`.

    It is a crude stem and it is meant to be. A desk holds a few dozen lines the
    person wrote themselves, where a false neighbour («залп» for «зал») costs
    one row in a list of five, while a real stemmer costs a dependency for every
    language we ever ship in — and the price of getting it wrong here is the
    opposite of retrieval's usual one: a fact that is not found is a fact the
    mouth asks about for the second time.
    """
    if left == right:
        return True
    shared = 0
    for a, b in zip(left, right):
        if a != b:
            break
        shared += 1
    return shared >= MIN_SHARED and shared >= min(STEM, len(left), len(right))


def _hits(asked: Sequence[str], line: str) -> int:
    """How many of the asked words this line carries. Words, not characters:
    a substring match would count «зал» inside «взгляд»."""
    found = words(line)
    return sum(1 for needle in asked if any(same_word(needle, word) for word in found))


def last_touched(subject_id: str, instances: Sequence[Instance]) -> datetime | None:
    """When this practice last stood on the desk.

    A cue carries no stamp of its own ([04] Cue) and one is not invented here.
    Freshness comes from the thing the desk does record — the practice's newest
    case — which is also what «уже было» is asking about. No case, no date; the
    fact still comes back, it just sorts last among equals.
    """
    stamps = [row.when for row in instances if row.subject_id == subject_id]
    return max(stamps) if stamps else None


def search_facts(
    query: str,
    cues: Sequence[Cue],
    *,
    subjects: Sequence[Subject] = (),
    instances: Sequence[Instance] = (),
    subject_id: str | None = None,
    limit: int = MAX_FACTS,
) -> list[Fact]:
    """The person's own facts that answer this query, best first.

    Order, and every step of it is a number: words of the query found in the
    cue's own text, then words found in the name of its practice (a line about
    the bike answers «велосипед» even when it never says the word), then that
    practice's freshness, then the desk's own order with the last written
    first. Two runs over the same desk rank the same way; nothing here reads a
    clock or a random seed.

    Nothing matched is an empty list, and that is an answer — «не нашёл». The
    alternative is a fact the person never said.
    """
    asked = query_words(query)
    if not asked:
        return []
    titles = {row.id: row.title for row in subjects}
    ranked: list[_Ranked] = []
    for position, cue in enumerate(cues):
        if subject_id is not None and cue.subject_id != subject_id:
            continue
        text_hits = _hits(asked, cue.text)
        title_hits = _hits(asked, titles.get(cue.subject_id, ""))
        if not text_hits and not title_hits:
            continue
        when = last_touched(cue.subject_id, instances)
        ranked.append(
            _Ranked(
                text_hits=text_hits,
                title_hits=title_hits,
                when=when,
                position=position,
                fact=Fact(
                    cue_id=cue.id,
                    subject_id=cue.subject_id,
                    text=cue.text,
                    surface=cue.surface,
                    practice_last_done=when,
                ),
            )
        )
    # Stable sorts, least significant first: the weaker key only ever breaks a
    # tie the stronger one left. Written as one composite key it would need a
    # sentinel date for a practice that never ran, and that sentinel is exactly
    # the invented stamp `last_touched` refuses to make up.
    ranked.sort(key=lambda row: row.position, reverse=True)
    ranked.sort(key=lambda row: (row.when is not None, row.when or datetime.min), reverse=True)
    ranked.sort(key=lambda row: (row.text_hits, row.title_hits), reverse=True)
    return [row.fact for row in ranked[:limit]]
