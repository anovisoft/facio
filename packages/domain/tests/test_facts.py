"""В3.3 — retrieval over the person's own facts, and only those.

The ranking is arithmetic, so it is pinned like arithmetic: same desk, same
order, every run. What is deliberately *not* here is a corpus — every fact in
these tests was written by the person on this desk (never-do #23, AI #3).
"""

from __future__ import annotations

from datetime import datetime, timedelta

from facio_domain.cues import add_cue
from facio_domain.desk import founding_desk
from facio_domain.facts import MAX_FACTS, query_words, same_word, search_facts
from facio_domain.models import Cue, CueSurface, Instance, InstanceStatus, Subject
from facio_domain.tools import QUERY_REQUIRED, apply_tool

NOW = datetime(2026, 8, 15, 12, 0, 0)


def _cue(cue_id: str, subject_id: str, text: str) -> Cue:
    return add_cue(id=cue_id, subject_id=subject_id, kind="correction", text=text, surface="do-time")


def _subject(subject_id: str, title: str) -> Subject:
    return Subject(id=subject_id, title=title, cadence={"count": 2, "period": "week"})


def _instance(subject_id: str, when: datetime) -> Instance:
    return Instance(
        id=f"{subject_id}-{when.isoformat()}",
        subject_id=subject_id,
        when=when,
        status=InstanceStatus.completed,
    )


def _apply(desk, name: str, arguments: dict):
    return apply_tool(desk, name, arguments, pain=False, now=NOW)


# --- the law --------------------------------------------------------------


def test_a_question_finds_the_line_the_person_wrote() -> None:
    cues = [
        _cue("brace", "push-ups", "держи корпус и ягодицы, не поясницу"),
        _cue("door", "bike", "зал до 22"),
    ]
    found = search_facts("что там было про поясницу?", cues)
    assert [fact.cue_id for fact in found] == ["brace"]
    assert found[0].text == "держи корпус и ягодицы, не поясницу"
    assert found[0].surface == CueSurface.do_time


def test_an_inflected_word_is_the_same_word() -> None:
    """«поясницей» and «поясницу» are one word to the person. Equality alone
    would find neither from the other, and the fact would be asked for twice."""
    assert same_word("поясницей", "поясницу")
    assert same_word("спина", "спину")
    assert same_word("зал", "зала")
    cues = [_cue("brace", "push-ups", "держи корпус и ягодицы, не поясницу")]
    assert [fact.cue_id for fact in search_facts("поясницей", cues)] == ["brace"]


def test_a_shared_letter_or_two_is_not_a_shared_word() -> None:
    assert not same_word("run", "rug")
    assert not same_word("back", "bacon")
    assert not same_word("он", "она")
    cues = [_cue("bacon", "breakfast", "bacon and eggs")]
    assert search_facts("back", cues) == []


def test_the_line_itself_outranks_the_name_of_the_practice() -> None:
    """A line about the bike answers «велосипед» even when it never says the
    word — but a line that says it out loud is the better answer."""
    cues = [
        _cue("by-title", "bike", "не гони в горку"),
        _cue("by-text", "push-ups", "велосипед стоит в коридоре"),
    ]
    subjects = [_subject("bike", "велосипед"), _subject("push-ups", "отжимания")]
    found = search_facts("велосипед", cues, subjects=subjects)
    assert [fact.cue_id for fact in found] == ["by-text", "by-title"]


def test_more_of_the_asked_words_wins() -> None:
    cues = [
        _cue("one", "push-ups", "держи корпус"),
        _cue("two", "push-ups", "держи корпус и ягодицы, не поясницу"),
    ]
    found = search_facts("корпус поясница", cues)
    assert [fact.cue_id for fact in found] == ["two", "one"]


def test_freshness_breaks_a_tie() -> None:
    """Same words matched, so the practice that actually happened last week
    answers before the one that has been silent for three."""
    cues = [
        _cue("silent", "bike", "спина держится ровно"),
        _cue("fresh", "push-ups", "спина держится ровно"),
    ]
    instances = [
        _instance("bike", NOW - timedelta(days=21)),
        _instance("push-ups", NOW - timedelta(days=1)),
    ]
    found = search_facts("спина", cues, instances=instances)
    assert [fact.cue_id for fact in found] == ["fresh", "silent"]
    assert found[0].practice_last_done == NOW - timedelta(days=1)


def test_a_fact_on_a_practice_that_never_ran_still_comes_back() -> None:
    """No case on the desk is no date — not a made-up one, and not a reason to
    drop the line the person wrote."""
    cues = [_cue("brace", "push-ups", "держи корпус")]
    found = search_facts("корпус", cues)
    assert [fact.cue_id for fact in found] == ["brace"]
    assert found[0].practice_last_done is None


def test_the_last_written_of_two_equals_comes_first() -> None:
    cues = [
        _cue("older", "push-ups", "держи корпус"),
        _cue("newer", "push-ups", "держи корпус"),
    ]
    assert [fact.cue_id for fact in search_facts("корпус", cues)] == ["newer", "older"]


def test_a_question_made_only_of_stop_words_finds_nothing() -> None:
    """«а что там было?» names no fact. Answering it with the whole desk would
    read back facts the person never brought up."""
    cues = [_cue("brace", "push-ups", "держи корпус и ягодицы, не поясницу")]
    assert query_words("а что там было?") == []
    assert search_facts("а что там было?", cues) == []
    assert search_facts("what did we say about it?", cues) == []


def test_nothing_matched_is_an_empty_list() -> None:
    cues = [_cue("door", "bike", "зал до 22")]
    assert search_facts("медитация", cues) == []


def test_the_answer_stops_at_five() -> None:
    cues = [_cue(f"cue-{index}", "push-ups", "держи корпус") for index in range(9)]
    found = search_facts("корпус", cues)
    assert len(found) == MAX_FACTS == 5
    # The last written win, and they stay in that order.
    assert [fact.cue_id for fact in found] == [f"cue-{index}" for index in (8, 7, 6, 5, 4)]


def test_a_subject_narrows_the_search() -> None:
    cues = [
        _cue("push", "push-ups", "держи корпус"),
        _cue("bike", "bike", "держи корпус"),
    ]
    found = search_facts("корпус", cues, subject_id="bike")
    assert [fact.cue_id for fact in found] == ["bike"]
    # A subject that is not on this desk matches nothing at all — it does not
    # quietly widen back to every practice.
    assert search_facts("корпус", cues, subject_id="rowing") == []


def test_a_word_is_matched_as_a_word_not_as_a_substring() -> None:
    cues = [_cue("look", "bike", "взгляд вперёд")]
    assert search_facts("зал", cues) == []


def test_english_and_russian_are_searched_the_same_way() -> None:
    cues = [_cue("brace", "push-ups", "brace the core and the glutes, not the lower back")]
    found = search_facts("what did we write down about my lower back?", cues)
    assert [fact.cue_id for fact in found] == ["brace"]


# --- through the tool -----------------------------------------------------


def test_search_facts_leaves_the_desk_untouched() -> None:
    """A search is reading. Refusal is not a mutation and neither is a hit."""
    desk = founding_desk(now=NOW)
    outcome = _apply(desk.model_copy(deep=True), "search_facts", {"query": "зал"})
    assert outcome.ok is True
    assert outcome.mutated is False
    assert outcome.snapshot_widget_ids == []
    assert outcome.desk == desk
    assert [row["cue_id"] for row in outcome.data["facts"]] == ["bike-gym-hours"]


def test_an_empty_query_is_refused_by_name() -> None:
    desk = founding_desk(now=NOW)
    outcome = _apply(desk, "search_facts", {"query": "   "})
    assert outcome.ok is False
    assert outcome.error == QUERY_REQUIRED
    assert outcome.desk == desk


def test_finding_nothing_is_ok_not_an_error() -> None:
    """«не нашёл» is an answer the mouth can say. An error here would push the
    turn into inventing something plausible instead."""
    desk = founding_desk(now=NOW)
    outcome = _apply(desk, "search_facts", {"query": "квэкснутый зонд"})
    assert outcome.ok is True
    assert outcome.error is None
    assert outcome.data == {"facts": []}


def test_the_tool_answers_the_founding_question() -> None:
    """«поясница уже была»: the conclusion written in an earlier turn is found
    from a later one, and the desk is not touched to find it."""
    written = _apply(
        founding_desk(now=NOW),
        "add_cue",
        {
            "id": "push-ups-brace-talk",
            "subject_id": "push-ups",
            "kind": "correction",
            "text": "держи корпус и ягодицы, не поясницу",
            "surface": "do-time",
        },
    )
    assert written.ok
    outcome = _apply(written.desk.model_copy(deep=True), "search_facts", {"query": "поясница"})
    facts = outcome.data["facts"]
    assert [row["cue_id"] for row in facts] == ["push-ups-brace-talk"]
    assert facts[0]["subject_id"] == "push-ups"
    assert facts[0]["surface"] == "do-time"
    assert outcome.desk == written.desk
