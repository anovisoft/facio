"""One talk turn: policy → model with tools → validated patch."""

from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any

from facio_domain.models import CueOrigin, Desk, Subject
from facio_domain.pain import reports_pain
from facio_domain.slots import occurrences_promised
from facio_domain.tools import apply_tool, snapshot_cards

from facio_api.providers.types import ModelProvider, ModelTurn
from facio_api.talk.schemas import (
    Locale,
    SnapshotCard,
    TalkTurnRequest,
    TalkTurnResponse,
    ToolCallRecord,
)
from facio_api.talk.spec import SYSTEM_PROMPT, tool_schemas

MAX_ROUNDS = 8
MAX_UTTERANCE = 4000
# One nudge after a first turn that wrote nothing: saying «записал» without a
# write is the bug it exists for. The carve-out is narrow on purpose — only a
# request the desk already satisfies exactly, which is the «одним виджетом»
# turn (Q34). Widening it to «записывать нечего» costs real writes.
EMPTY_TOOLS_NUDGE = (
    "Запись на стол — вызови инструмент сейчас. Не пересказывай правила. "
    "Если человек просит то, что на столе уже ровно так, ничего не вызывай. "
    "Человеку потом только короткая фраза."
)
EMPTY_TOOLS_NUDGE_EN = (
    "A desk write — call the tool now. Do not retell the rules. "
    "If they asked for what the desk already holds exactly, call nothing. "
    "Afterwards the person gets one short sentence."
)
SELECTION_BOUND = (
    "The person selected this phrase in your answer and asked what it means: «{quote}». "
    "It belongs to subject {subject_id}{step}. "
    "Answer them, and write that answer down with add_cue: kind clarification, "
    "surface on-demand, quote exactly «{quote}»{step_arg}."
)
SELECTION_ORPHAN = (
    "The person selected this phrase in your answer and asked what it means: «{quote}». "
    "Nothing on the desk is bound to it — no subject, no widget. "
    "Answer in text only. Do not call add_cue and do not hang it on some other practice."
)
# A clarification that lost the phrase it explains is half a cue: the answer is
# on the desk and nobody can tell what the question was. 05 calls a selection
# the strongest signal about what needed remembering, and `quote` is what
# carries it — so a missing one is refused by field name, the same way
# `surface_required` is, and the turn writes itself right on the next round.
# Never filled in from the selection behind the model's back (never-do AI #2).
QUOTE_REQUIRED = "quote_required"
# A link on a cue may only be the one the person themselves put in the
# conversation. «Model-invented image URLs — hallucinated links, dead hotlinks,
# and a wrong picture on a movement is worse than none» is a named trap in 06
# (#23), and a wish in the prompt is not a lock: the URL is **checked**. It has
# to occur verbatim in what the person wrote — this utterance or their own
# messages in the thread. It does not, the call comes back named, the way
# `quote_required` and `surface_required` do, and the turn can write itself
# right on the next round. Nothing is normalised, completed or looked up on the
# model's behalf — repairing a URL for it would be the same silent desk edit as
# filling in a quote (never-do AI #2). A malformed `media` is left to the law,
# which names it `invalid_media`.
MEDIA_NOT_IN_CONVERSATION = "media_not_in_conversation"
# Chips offered by a turn that is bound to nothing. 03 allows the row «only
# inside a turn that already has a binding», and it is the same rule that
# refuses an orphan cue (05): with no subject and no widget behind it, an
# offer is about nothing, and «пн, ср, пт» tapped into a void would be the
# desk inventing a practice to hang it on. The binding is whatever this turn
# already put on the table — what the client named (a selection, the widget
# the sheet stands over) or what a tool call of this turn just named itself —
# and it is resolved by `selection_subject_id`'s own resolver, not a second
# copy of it. Refused by name, like `quote_required`, so the turn can bind
# first and offer after.
CHIPS_UNBOUND = "chips_unbound"
LOCALE_LINE: dict[Locale, str] = {
    "ru": "The person writes in Russian: answer in Russian.",
    "en": "The person writes in English: answer in English.",
}
_LEAK_NEEDLES = (
    "инструмент",
    "focused_widget",
    "bike-reminder",
    "set_reminder",
    "thaw_subject",
    "freeze_subject",
    "умолчани",
    "tool_call",
    "tool",
)
_FALLBACK: dict[Locale, tuple[str, str, str]] = {
    "ru": (
        "Готово.",
        "Могу объяснить или записать на стол — напиши ещё раз.",
        "Записал бы на стол — напиши ещё раз короче.",
    ),
    "en": (
        "Done.",
        "I can explain it or put it on the desk — say it once more.",
        "I would put that on the desk — say it once more, shorter.",
    ),
}


def _nudge(locale: Locale) -> str:
    return EMPTY_TOOLS_NUDGE_EN if locale == "en" else EMPTY_TOOLS_NUDGE


def _human_text(text: str, *, mutated: bool, locale: Locale = "ru") -> str:
    done, empty, leaked = _FALLBACK.get(locale, _FALLBACK["ru"])
    compact = text.strip()
    if not compact:
        return done if mutated else empty
    lower = compact.casefold()
    if any(needle in lower for needle in _LEAK_NEEDLES):
        return done if mutated else leaked
    return compact


class TalkError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


async def run_turn(
    body: TalkTurnRequest,
    provider: ModelProvider,
    *,
    now: datetime | None = None,
) -> TalkTurnResponse:
    utterance = body.utterance.strip()
    if not utterance:
        raise TalkError(422, "utterance required")
    if len(utterance) > MAX_UTTERANCE:
        raise TalkError(422, "utterance too long")
    stamp = now or body.now or datetime.now()
    pain = reports_pain(utterance)
    desk = body.desk.model_copy(deep=True)
    origin = CueOrigin(chat_id=body.thread_id, message_id=None)
    messages = _messages(body, utterance, pain)
    records: list[ToolCallRecord] = []
    mutated = False
    snapshot_ids: list[str] = []
    text = ""
    # What the person was told before the nudge went in. The nudge is a message
    # from us, not from them, so a reply written to it is a reply to the wrong
    # question — «Понял, буду писать сразу» instead of the answer. Kept, and
    # used when the nudge produced no write after all.
    text_before_nudge = ""
    tools = tool_schemas()
    first_complete = True
    # What this turn is bound to. Seeded with what the client named, then grown
    # by every successful call that names a subject of its own — «only inside a
    # turn that already has a binding» (03), read literally: by the time chips
    # are offered, something in this turn is about something.
    bound = turn_bindings(body)
    # The row above the composer. A later successful `offer_chips` replaces the
    # earlier one rather than adding to it: there is one row, it lives for one
    # turn, and two calls are a turn rewriting its own offer, not a row of six.
    reply_chips: list[str] = []

    for _ in range(MAX_ROUNDS):
        turn = await provider.complete(messages, tools)
        if turn.tool_calls:
            first_complete = False
            messages.append(_assistant_tools(turn))
            for call in turn.tool_calls:
                if _selection_quote_missing(body, call.name, call.arguments):
                    ok, error, data = False, QUOTE_REQUIRED, None
                elif _media_not_in_conversation(body, utterance, call.name, call.arguments):
                    ok, error, data = False, MEDIA_NOT_IN_CONVERSATION, None
                elif call.name == "offer_chips" and not bound:
                    ok, error, data = False, CHIPS_UNBOUND, None
                else:
                    outcome = apply_tool(
                        desk,
                        call.name,
                        call.arguments,
                        pain=pain,
                        now=stamp,
                        origin=origin,
                    )
                    desk = outcome.desk
                    ok, error, data = outcome.ok, outcome.error, outcome.data
                    if outcome.mutated:
                        mutated = True
                        snapshot_ids.extend(outcome.snapshot_widget_ids)
                    if outcome.ok:
                        named = call_binding(desk, call.arguments)
                        if named is not None:
                            bound.add(named)
                        if call.name == "offer_chips":
                            reply_chips = list(data.get("chips", []))
                records.append(
                    ToolCallRecord(
                        name=call.name,
                        arguments=call.arguments,
                        ok=ok,
                        error=error,
                    )
                )
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": json.dumps(
                            {"ok": ok, "error": error, "data": data},
                            ensure_ascii=False,
                            default=str,
                        ),
                    }
                )
            continue
        text = (turn.text or "").strip()
        if first_complete:
            first_complete = False
            text_before_nudge = text
            messages.append({"role": "assistant", "content": turn.text or ""})
            messages.append({"role": "user", "content": _nudge(body.locale)})
            continue
        break

    # The nudge asked for a write and got none, so there was nothing to write:
    # the answer the person is owed is the one written to *them*, before we
    # interrupted. With a write it is the other way round — the later sentence
    # is the one that knows what landed.
    #
    # The test is **a write**, not «a tool ran». It used to read `not records`,
    # which counts any call at all, and half the tool block writes nothing:
    # `list_desk`, `get_subject`, `list_cues`, and now `search_facts` and
    # `offer_chips` — the last of which the prompt actively asks for before a
    # question. A turn that chatted, got nudged, looked something up and then
    # said «Понял, ничего не записываю» handed that sentence to the person and
    # threw away the answer they were owed. Same shape the PO saw on the phone
    # as «Напомню в эти семь часов». A failed write is not a write either:
    # nothing landed, so nothing knows better than the sentence written to them.
    if not mutated and text_before_nudge:
        text = text_before_nudge
    text = _human_text(text, mutated=mutated, locale=body.locale)
    cards = [SnapshotCard.model_validate(row) for row in snapshot_cards(desk, snapshot_ids)] if mutated else []
    return TalkTurnResponse(
        text=text,
        desk=desk,
        mutated=mutated,
        snapshots=cards,
        tool_calls=records,
        thread_id=body.thread_id,
        reply_chips=reply_chips,
    )


def _subject_brief(subject: Subject, day: date) -> dict[str, Any]:
    """One subject as the mouth sees it.

    A practice that promises several occurrences in one period carries two more
    facts: that the lid draws them as **one tile**, and the hours they stand on
    (Q34). Both are here because «помести их в один виджет» is a question about
    what is already true — without them the mouth guesses, and its guess is
    set_reminder over the same seven hours, which is «записал» about nothing.

    They are added **only** for such a practice. Handed the hours of every
    subject, the mouth starts reading the founding turns as already written —
    «зал до 22 уже записан», «в 19 уже стоит» — and the desk stops learning
    what the person just said. Measured, not guessed: with the hours on every
    subject the 4 → 30 progression stopped landing on 3 of 6 live runs.
    """
    brief: dict[str, Any] = {
        "id": subject.id,
        "title": subject.title,
        "cadence": subject.cadence.model_dump(mode="json"),
        "target": subject.target.model_dump() if subject.target else None,
        "status": subject.status,
    }
    if occurrences_promised(subject, day) > 1:
        brief["one_tile"] = True
        brief["hours"] = [
            hour.isoformat(timespec="minutes") for hour in (subject.window.hours if subject.window else [])
        ]
    return brief


def _messages(body: TalkTurnRequest, utterance: str, pain: bool) -> list[dict[str, Any]]:
    day = (body.now or datetime.now()).date()
    desk_brief = json.dumps(
        {
            "subjects": [_subject_brief(subject, day) for subject in body.desk.subjects],
            "widgets": [
                {
                    "id": widget.id,
                    "type": widget.type,
                    "title": widget.title,
                    "section": widget.section,
                    "subject_id": widget.subject_id,
                }
                for widget in body.desk.widgets
            ],
            "focused_widget_id": body.focused_widget_id,
            "pain": pain,
        },
        ensure_ascii=False,
        default=str,
    )
    # The first system message is the whole stable prefix — prompt plus the
    # language line — and nothing per-request may join it. Everything that
    # changes per turn (the desk, the selection) goes after it, because a
    # prompt cache is a prefix match: one byte earlier in the prefix and the
    # rest of the request stops being reusable. Providers cache on this block.
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": f"{SYSTEM_PROMPT}\n\n{LOCALE_LINE[body.locale]}"},
        {"role": "system", "content": f"Стол сейчас:\n{desk_brief}"},
    ]
    if body.selection is not None:
        messages.append({"role": "system", "content": selection_line(body)})
    for row in body.thread[-20:]:
        role = row.role if row.role in {"user", "assistant"} else "user"
        messages.append({"role": role, "content": row.text})
    messages.append({"role": "user", "content": utterance})
    return messages


def selection_subject_id(body: TalkTurnRequest) -> str | None:
    """The subject a selection hangs on, or None — the desk decides, not the model.

    Only a binding the client actually named counts: the subject, the widget the
    selection came from, or the widget the sheet was opened over. The
    default-subject guesswork of an ordinary turn (reps → push-ups, an hour →
    bike) is deliberately not reused here: guessing would manufacture the orphan
    the RFC forbids, just filed under a practice that was standing nearby.
    """
    selection = body.selection
    if selection is None:
        return None
    named = _subject_on_desk(body.desk, selection.subject_id)
    if named is not None:
        return named
    for widget_id in (selection.widget_id, body.focused_widget_id):
        behind = _subject_behind(body.desk, widget_id)
        if behind is not None:
            return behind
    return None


def _subject_on_desk(desk: Desk, subject_id: Any) -> str | None:
    """A subject id, but only if this desk actually carries it."""
    if not isinstance(subject_id, str) or not subject_id:
        return None
    return subject_id if any(row.id == subject_id for row in desk.subjects) else None


def _subject_behind(desk: Desk, widget_id: Any) -> str | None:
    """The subject a widget belongs to. The one place widget → subject is read."""
    if not isinstance(widget_id, str) or not widget_id:
        return None
    for widget in desk.widgets:
        if widget.id == widget_id:
            return _subject_on_desk(desk, widget.subject_id)
    return None


def turn_bindings(body: TalkTurnRequest) -> set[str]:
    """What the **client** bound this turn to, before the model has spoken.

    The same question `selection_subject_id` answers for a selected phrase,
    asked of the turn as a whole, and answered by the same resolver: a
    selection's binding, or the widget the composer is standing over. The
    default-subject guesswork of the prompt (reps → push-ups, an hour → bike)
    is not reused here either — a guess would manufacture the binding whose
    absence is the whole point of the check.
    """
    bound: set[str] = set()
    for subject_id in (selection_subject_id(body), _subject_behind(body.desk, body.focused_widget_id)):
        if subject_id is not None:
            bound.add(subject_id)
    return bound


def call_binding(desk: Desk, arguments: dict[str, Any]) -> str | None:
    """The subject a call of this turn just put on the table, if it named one.

    A turn that wrote an hour onto the bike is bound to the bike, and may offer
    the person a row about it. A turn that only looked around — `list_desk`, a
    search with no practice named — bound nothing and may not.
    """
    named = _subject_on_desk(desk, arguments.get("subject_id"))
    if named is not None:
        return named
    return _subject_behind(desk, arguments.get("widget_id"))


def _selection_quote_missing(
    body: TalkTurnRequest, name: str, arguments: dict[str, Any]
) -> bool:
    """A bound selection writing a cue without the phrase it explains.

    Only fires on the turn that carries a selection with a real binding — an
    ordinary `add_cue` (a correction from talk) has no phrase to quote and is
    left alone.
    """
    if name != "add_cue":
        return False
    if body.selection is None or selection_subject_id(body) is None:
        return False
    quote = arguments.get("quote")
    return not (isinstance(quote, str) and quote.strip())


def _human_words(body: TalkTurnRequest, utterance: str) -> list[str]:
    """Everything in this turn that the **person** wrote.

    The assistant's half of the thread is deliberately left out: a URL it
    produced two rounds ago is precisely the invention this check exists to
    catch, and letting the model quote itself would launder one.
    """
    rows = [utterance, body.utterance]
    rows.extend(row.text for row in body.thread if row.role == "user")
    return [row for row in rows if row]


def _media_not_in_conversation(
    body: TalkTurnRequest, utterance: str, name: str, arguments: dict[str, Any]
) -> bool:
    """A `link` whose URL is nowhere in the person's own words.

    Verbatim means verbatim: the URL string is looked for as it was passed, with
    no trimming, no case folding and no scheme guessing. A URL that has to be
    repaired to match was not the one the person sent. `photo` is not checked
    here — its `ref` is a handle the client hands over with the picture, not
    something the model can hallucinate into a working image; the day an
    attachment path exists, that ref is checked against the client, not the text.
    """
    if name != "add_cue":
        return False
    media = arguments.get("media")
    if not isinstance(media, dict) or media.get("kind") != "link":
        return False
    url = media.get("url")
    if not isinstance(url, str) or not url.strip():
        # Shapeless media is the law's to refuse, by its own field name.
        return False
    return not any(url in row for row in _human_words(body, utterance))


def selection_line(body: TalkTurnRequest) -> str:
    selection = body.selection
    assert selection is not None
    subject_id = selection_subject_id(body)
    if subject_id is None:
        return SELECTION_ORPHAN.format(quote=selection.quote)
    step_id = (selection.step_id or "").strip() or None
    return SELECTION_BOUND.format(
        quote=selection.quote,
        subject_id=subject_id,
        step=f", step {step_id}" if step_id else "",
        step_arg=f", step_id {step_id}" if step_id else "",
    )


def _assistant_tools(turn: ModelTurn) -> dict[str, Any]:
    return {
        "role": "assistant",
        "content": turn.text or None,
        "tool_calls": [
            {
                "id": call.id,
                "type": "function",
                "function": {
                    "name": call.name,
                    "arguments": json.dumps(call.arguments, ensure_ascii=False),
                },
            }
            for call in turn.tool_calls
        ],
    }
