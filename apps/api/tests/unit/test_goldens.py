from __future__ import annotations

from datetime import datetime, time

from facio_domain.desk import founding_desk
from facio_domain.drift import drift_card
from facio_domain.models import CueKind, CueSurface, Desk, SubjectStatus, WidgetType
from facio_domain.tools import apply_tool, times_per_week

from facio_api.providers.scripted import ScriptedProvider
from facio_api.providers.types import ModelToolCall, ModelTurn
from facio_api.talk.goldens import load_goldens, match_golden
from facio_api.talk.loop import MEDIA_NOT_IN_CONVERSATION, run_turn
from facio_api.talk.schemas import TalkSelection, TalkTurnRequest

NOW = datetime(2026, 8, 15, 12, 0, 0)
SEED_BRACE = "держи корпус и ягодицы"
FOUNDING_IDS = {"bike", "push-ups", "vegetables"}


class QuotelessProvider:
    """Writes the clarification without its quote, then with it.

    Exactly the live failure R3-B measured: `surface` and `kind` right, the
    phrase itself dropped.
    """

    def __init__(self) -> None:
        self._round = 0

    async def complete(self, messages, tools):
        del messages, tools
        self._round += 1
        base = {
            "subject_id": "push-ups",
            "step_id": "rep-1",
            "kind": "clarification",
            "surface": "on-demand",
            "text": "таз в одну линию с плечами и пятками",
        }
        if self._round == 1:
            return ModelTurn(
                tool_calls=[
                    ModelToolCall(id="c1", name="add_cue", arguments={"id": "push-ups-quoteless", **base})
                ]
            )
        if self._round == 2:
            return ModelTurn(
                tool_calls=[
                    ModelToolCall(
                        id="c2",
                        name="add_cue",
                        arguments={"id": "push-ups-quoted", **base, "quote": "не роняй таз"},
                    )
                ]
            )
        return ModelTurn(text="Таз держи в одной линии с плечами и пятками.")


def _request(utterance: str, selection: TalkSelection | None = None) -> TalkTurnRequest:
    return TalkTurnRequest(
        utterance=utterance,
        desk=founding_desk(now=NOW),
        thread=[],
        thread_id="golden",
        now=NOW,
        selection=selection,
    )


async def _play(utterance: str, selection: TalkSelection | None = None):
    return await run_turn(
        _request(utterance, selection),
        ScriptedProvider.for_utterance(utterance),
        now=NOW,
    )


async def _play_golden(golden):
    """Replay a golden the way the client sends it — selection included."""
    return await _play(golden.utterance, golden.selection)


def _names(result) -> list[str]:
    return [call.name for call in result.tool_calls]


def _subject(desk: Desk, subject_id: str):
    return next(row for row in desk.subjects if row.id == subject_id)


def _sentences(text: str) -> list[str]:
    chunks = text.replace("!", ".").replace("?", ".").split(".")
    return [part.strip() for part in chunks if part.strip()]


RUSSIAN_IDS = {
    "cadence_shrink",
    "checklist_shopping",
    "clarification_orphan",
    "clarification_selection",
    "cue_link_invented",
    "cue_with_link",
    "drift_answer",
    "explain_only",
    "gym_no_clock",
    "gym_until_22",
    "lower_back",
    "method_4_to_30",
    "miss_skip",
    "named_hour_beats_closing",
    "pain_raise",
    "pain_skip_freeze",
    "remind_at_19",
    "stepper_warmup",
    "thaw_pause",
    "timer_meditation",
}


def test_goldens_are_present() -> None:
    ids = {golden.id for golden in load_goldens()}
    assert {row for row in ids if not row.endswith("_en")} == RUSSIAN_IDS


def test_match_lower_back() -> None:
    golden = match_golden("поясница забирает нагрузку")
    assert golden is not None
    assert golden.id == "lower_back"


async def test_lower_back_writes_do_time_cue() -> None:
    golden = match_golden("поясница забирает нагрузку")
    assert golden is not None
    result = await _play(golden.utterance)
    assert result.mutated is True
    assert [call.name for call in result.tool_calls] == golden.expect.tools
    cue = next(row for row in result.desk.cues if row.subject_id == "push-ups" and row.id.endswith("talk"))
    assert cue.surface == CueSurface.do_time
    for needle in golden.expect.cue.text_contains if golden.expect.cue else []:
        assert needle in cue.text
    assert result.snapshots
    assert result.snapshots[0].widget_id == "push-ups-counter"
    assert "корпус" in result.snapshots[0].line


async def test_pain_raise_does_not_lift_target() -> None:
    golden = match_golden("больно, давай 40")
    assert golden is not None
    result = await _play(golden.utterance)
    names = [call.name for call in result.tool_calls]
    assert names == golden.expect.tools
    assert result.tool_calls[0].ok is False
    assert result.tool_calls[0].error == "pain_forbids_raise"
    goal = next(row.target.goal for row in result.desk.subjects if row.id == "push-ups")
    assert goal <= (golden.expect.target_goal_max or 30)
    assert any(call.name == "add_cue" and call.ok for call in result.tool_calls)


async def test_explain_only_has_no_card() -> None:
    golden = match_golden("что значит держать корпус?")
    assert golden is not None
    result = await _play(golden.utterance)
    assert result.mutated is False
    assert result.snapshots == []
    assert result.tool_calls == []
    assert result.text


async def test_method_4_to_30_writes_current_and_cue() -> None:
    golden = match_golden("могу 4, хочу 30 подряд, как?")
    assert golden is not None
    assert golden.id == "method_4_to_30"
    result = await _play(golden.utterance)
    names = _names(result)
    assert result.mutated is True
    assert names[0] in {"list_desk", "get_widget", "get_subject"}
    assert "update_widget" in names
    assert "add_cue" in names
    assert "set_reminder" not in names
    for name in golden.expect.forbidden_tools:
        assert name not in names
    update = next(call for call in result.tool_calls if call.name == "update_widget")
    assert update.arguments["widget_id"] == "push-ups-counter"
    assert update.arguments["target"] == 30
    assert update.arguments["count"] == 4
    if "set_cadence" in names:
        cadence_call = next(call for call in result.tool_calls if call.name == "set_cadence")
        assert int(cadence_call.arguments["count"]) <= 3
    push = _subject(result.desk, "push-ups")
    assert push.target is not None
    assert push.target.current == 4
    assert push.target.goal == 30
    assert times_per_week(push.cadence) <= 3
    cue = next(row for row in result.desk.cues if row.subject_id == "push-ups" and row.id.endswith("talk"))
    assert cue.surface == CueSurface.do_time
    # The method changes *how* it is done: correction at do-time, not an
    # explanation filed behind a «?» ([04] Cue defaults).
    assert golden.expect.cue is not None
    assert golden.expect.cue.kind == "correction"
    assert cue.kind == CueKind.correction
    assert cue.text != SEED_BRACE
    for needle in golden.expect.cue.text_contains if golden.expect.cue else []:
        assert needle in cue.text
    assert result.snapshots
    assert any(card.widget_id == "push-ups-counter" for card in result.snapshots)
    assert len(_sentences(result.text)) >= 2


async def test_gym_no_clock_creates_counter_without_reminder() -> None:
    golden = match_golden("запиши зал")
    assert golden is not None
    assert golden.id == "gym_no_clock"
    result = await _play(golden.utterance)
    names = _names(result)
    assert result.mutated is True
    assert "create_widget" in names
    assert "set_reminder" not in names
    create = next(call for call in result.tool_calls if call.name == "create_widget")
    assert create.arguments["type"] == "counter"
    subject_id = create.arguments["subject_id"]
    assert subject_id not in FOUNDING_IDS
    reminders = [
        row for row in result.desk.widgets if row.subject_id == subject_id and row.type == WidgetType.reminder
    ]
    assert reminders == []
    # No hour — still a rhythm. A practice without one is a planner line (06 #14).
    assert golden.expect.cadence is not None
    assert create.arguments["cadence"]["period"] == golden.expect.cadence.period
    gym = _subject(result.desk, subject_id)
    assert gym.cadence.period == golden.expect.cadence.period
    assert gym.cadence.count == golden.expect.cadence.count
    assert times_per_week(gym.cadence) >= 1
    bike = _subject(result.desk, "bike")
    assert bike.window is not None
    assert bike.window.latest_by == time(19, 0)
    assert any(row.id == "bike-reminder" for row in result.desk.widgets)


async def test_miss_skip_does_not_hang_a_clock() -> None:
    golden = match_golden("сегодня не сходил")
    assert golden is not None
    assert golden.id == "miss_skip"
    result = await _play(golden.utterance)
    names = _names(result)
    assert result.mutated is True
    assert "skip" in names
    assert "set_reminder" not in names
    skip = next(call for call in result.tool_calls if call.name == "skip")
    assert skip.ok is True
    assert skip.arguments["widget_id"] == "bike-reminder"
    bike = _subject(result.desk, "bike")
    assert bike.window is not None
    assert bike.window.latest_by == time(19, 0)


async def test_remind_at_19_uses_stated_hour() -> None:
    golden = match_golden("напомни в 19, в 21 я уже сплю")
    assert golden is not None
    assert golden.id == "remind_at_19"
    result = await _play(golden.utterance)
    names = _names(result)
    assert result.mutated is True
    reminder = next(call for call in result.tool_calls if call.name == "set_reminder")
    assert reminder.arguments["subject_id"] == "bike"
    assert reminder.arguments["latest_by"] in {"19:00", "19:00:00"}
    assert reminder.arguments.get("closes_at") not in {"21:00", "21:00:00"}
    bike = _subject(result.desk, "bike")
    assert bike.window is not None
    assert bike.window.latest_by == time(19, 0)
    assert bike.window.latest_by != time(18, 0)
    timing = [
        row
        for row in result.desk.cues
        if row.subject_id == "bike" and row.surface == CueSurface.timing
    ]
    assert any("сп" in row.text.casefold() for row in timing)
    assert "add_cue" in names


async def test_gym_until_22_is_arithmetic() -> None:
    golden = match_golden("зал до 22")
    assert golden is not None
    assert golden.id == "gym_until_22"
    result = await _play(golden.utterance)
    assert result.mutated is True
    reminder = next(call for call in result.tool_calls if call.name == "set_reminder")
    assert reminder.arguments["subject_id"] == "bike"
    assert reminder.arguments["closes_at"] in {"22:00", "22:00:00"}
    assert "latest_by" not in reminder.arguments
    bike = _subject(result.desk, "bike")
    assert bike.window is not None
    assert bike.window.latest_by == time(19, 0)
    assert bike.window.closes_at == time(22, 0)


async def test_named_hour_beats_closing_formula() -> None:
    golden = match_golden("к 23 он уже закрывается. Напоминай мне пойти в зал в 19 часов")
    assert golden is not None
    assert golden.id == "named_hour_beats_closing"
    result = await _play(golden.utterance)
    assert result.mutated is True
    reminder = next(call for call in result.tool_calls if call.name == "set_reminder")
    assert reminder.arguments["latest_by"] in {"19:00", "19:00:00"}
    assert reminder.arguments["closes_at"] in {"23:00", "23:00:00"}
    gym = _subject(result.desk, reminder.arguments["subject_id"])
    assert gym.window is not None
    assert gym.window.latest_by == time(19, 0)
    assert gym.window.closes_at == time(23, 0)
    fire = next(
        row.payload.fire_at
        for row in result.desk.widgets
        if row.subject_id == gym.id and row.type == WidgetType.reminder
    )
    assert fire is not None
    assert fire.hour == 19


async def test_cadence_shrink_does_not_raise_goal() -> None:
    golden = match_golden("давай раз в неделю")
    assert golden is not None
    assert golden.id == "cadence_shrink"
    result = await _play(golden.utterance)
    names = _names(result)
    assert result.mutated is True
    assert names[0] in {"shrink_subject", "set_cadence"}
    if "set_cadence" in names:
        cadence_call = next(call for call in result.tool_calls if call.name == "set_cadence")
        assert cadence_call.arguments["period"] == "week"
        assert int(cadence_call.arguments["count"]) == 1
        assert cadence_call.arguments["subject_id"] == "push-ups"
    else:
        shrink = next(call for call in result.tool_calls if call.name == "shrink_subject")
        assert shrink.arguments["subject_id"] == "push-ups"
    push = _subject(result.desk, "push-ups")
    assert times_per_week(push.cadence) <= 1
    assert push.target is not None
    assert push.target.goal <= 30


async def test_unknown_utterance_stays_text_only() -> None:
    utterance = "квэкснутый зонд 174"
    assert match_golden(utterance) is None
    result = await _play(utterance)
    assert result.mutated is False
    assert result.tool_calls == []


async def test_pain_skip_freeze_pauses_bike_without_raising() -> None:
    utterance = "сегодня пропустил, спина болела"
    golden = match_golden(utterance)
    assert golden is not None
    assert golden.id == "pain_skip_freeze"
    assert "сегодня не сходил" not in utterance
    result = await _play(golden.utterance)
    names = _names(result)
    assert result.mutated is True
    assert names == golden.expect.tools
    for name in golden.expect.forbidden_tools:
        assert name not in names
    skip = next(call for call in result.tool_calls if call.name == "skip")
    assert skip.arguments["widget_id"] == "bike-reminder"
    freeze = next(call for call in result.tool_calls if call.name == "freeze_subject")
    assert freeze.arguments["subject_id"] == "bike"
    assert freeze.ok is True
    bike = _subject(result.desk, "bike")
    assert bike.status == SubjectStatus.paused
    assert bike.paused_at == NOW
    push = _subject(result.desk, "push-ups")
    assert push.target is not None
    assert push.target.goal <= 30


def test_match_thaw_phrases() -> None:
    assert match_golden("отпустило").id == "thaw_pause"
    assert match_golden("спина прошла").id == "thaw_pause"
    assert match_golden("верни велосипед").id == "thaw_pause"


async def test_thaw_pause_restores_bike() -> None:
    golden = match_golden("отпустило")
    assert golden is not None
    assert golden.id == "thaw_pause"
    frozen = apply_tool(
        founding_desk(now=NOW),
        "freeze_subject",
        {"subject_id": "bike"},
        pain=False,
        now=NOW,
    )
    assert frozen.ok
    result = await run_turn(
        TalkTurnRequest(
            utterance=golden.utterance,
            desk=frozen.desk,
            thread=[],
            thread_id="golden",
            now=NOW,
        ),
        ScriptedProvider.for_utterance(golden.utterance),
        now=NOW,
    )
    names = _names(result)
    assert result.mutated is True
    assert names == golden.expect.tools
    bike = _subject(result.desk, "bike")
    assert bike.status == SubjectStatus.active
    assert bike.paused_at is None


# --- R3 selection → clarification ----------------------------------------


async def test_clarification_selection_lands_on_demand_with_the_quote() -> None:
    """The answer to a selected phrase comes back behind a `?`, carrying the phrase."""
    golden = match_golden("что это значит: не роняй таз?")
    assert golden is not None
    assert golden.id == "clarification_selection"
    assert golden.selection is not None
    result = await _play_golden(golden)
    assert result.mutated is True
    assert _names(result) == golden.expect.tools
    expected = golden.expect.cue
    assert expected is not None
    cue = next(row for row in result.desk.cues if row.id == "push-ups-hips-talk")
    assert cue.subject_id == expected.subject_id
    assert cue.kind == CueKind.clarification
    # Never inline at do-time: rep one has to stay readable (04, P9).
    assert cue.surface == CueSurface.on_demand
    assert cue.step_id == expected.step_id
    assert cue.quote == expected.quote
    assert cue.quote == golden.selection.quote
    for needle in expected.text_contains:
        assert needle in cue.text
    push = _subject(result.desk, "push-ups")
    assert cue.id in push.cue_ids
    # The founding do-time correction is untouched — the `?` did not take its place.
    brace = next(row for row in result.desk.cues if row.id == "push-ups-brace")
    assert brace.surface == CueSurface.do_time


async def test_clarification_selection_does_not_move_the_do_time_line() -> None:
    """A clarification is looked up; the tile still shows the correction (04)."""
    result = await _play_golden(match_golden("что это значит: не роняй таз?"))
    card = next(row for row in result.snapshots if row.widget_id == "push-ups-counter")
    assert "таз" not in card.line
    assert card.line.endswith("brace the core and the glutes")


async def test_clarification_orphan_stays_text_only() -> None:
    """A selection with no bound subject produces no cue (04, 05)."""
    golden = match_golden("что это значит: беговая экономичность?")
    assert golden is not None
    assert golden.id == "clarification_orphan"
    assert golden.selection is not None
    assert golden.selection.subject_id is None
    assert golden.selection.widget_id is None
    before = founding_desk(now=NOW)
    result = await _play_golden(golden)
    assert result.mutated is False
    assert result.tool_calls == []
    assert "add_cue" not in _names(result)
    assert result.snapshots == []
    assert result.desk.cues == before.cues
    assert result.text


# --- R4: the answer to drift only ever goes down ---------------------------


async def test_drift_answer_offers_less_and_never_more() -> None:
    """The ladder is the law's; the mouth may word it and write the shrink.

    What this golden holds is the one thing a model must never do with a
    practice that went quiet: answer it with a bigger number ([06] #21).
    """
    golden = match_golden("велосипед три недели стоит, что делать?")
    assert golden is not None
    assert golden.id == "drift_answer"
    before = _subject(founding_desk(now=NOW), "bike")
    result = await _play(golden.utterance)
    names = _names(result)
    assert result.mutated is True
    assert names == golden.expect.tools
    for name in golden.expect.forbidden_tools:
        assert name not in names
    cadence = next(call for call in result.tool_calls if call.name == "set_cadence")
    assert cadence.arguments["subject_id"] == "bike"
    assert cadence.arguments["period"] == "week"
    assert int(cadence.arguments["count"]) == 1
    bike = _subject(result.desk, "bike")
    assert times_per_week(bike.cadence) <= 1
    assert times_per_week(bike.cadence) < times_per_week(before.cadence)
    # Nothing was raised anywhere else on the desk to compensate.
    push = _subject(result.desk, "push-ups")
    assert push.target is not None
    assert push.target.goal <= (golden.expect.target_goal_max or 30)


async def test_drift_answer_does_not_read_the_ladder_back_to_the_person() -> None:
    result = await _play("велосипед три недели стоит, что делать?")
    lowered = result.text.casefold()
    for needle in ("постарайся", "срыв", "ступень", "drift"):
        assert needle not in lowered, needle


async def test_answering_in_talk_leaves_no_card_the_same_morning() -> None:
    """R13: the shrink went through the mouth, so the first rung stays quiet.

    Before this the person said «раз в неделю», the mouth shrank the bike, and
    the lid still handed him «перенести на сегодня?» about the same bike the
    same day — a second question about a thing he had already settled, with a
    bigger step than the rung was offering (Q28: once per period, same object).
    """
    desk = founding_desk(now=NOW)
    assert drift_card(desk.subjects, desk.instances, NOW) is not None

    result = await _play("велосипед три недели стоит, что делать?")
    bike = _subject(result.desk, "bike")
    assert bike.drift_asked_at == NOW
    assert drift_card(result.desk.subjects, result.desk.instances, NOW) is None
    # The rung did not move: nobody asked, and nobody refused.
    assert bike.drift_asks_made == 0
    assert bike.drift_retire_refusals == 0


# --- R4 addendum: a clarification without its quote is refused -------------


async def test_a_bound_selection_without_a_quote_is_refused_by_field_name() -> None:
    """`quote` carries the phrase the person pointed at (05). Missing it, the
    cue is half written — so the call comes back named, the way a missing
    `surface` does, and the turn can fix itself on the next round."""
    selection = TalkSelection(quote="не роняй таз", widget_id="push-ups-counter", step_id="rep-1")
    provider = QuotelessProvider()
    result = await run_turn(
        TalkTurnRequest(
            utterance="что это значит?",
            desk=founding_desk(now=NOW),
            thread=[],
            thread_id="golden",
            now=NOW,
            selection=selection,
        ),
        provider,
        now=NOW,
    )
    first = result.tool_calls[0]
    assert first.name == "add_cue"
    assert first.ok is False
    assert first.error == "quote_required"
    # The desk never took the quoteless cue.
    assert all(row.id != "push-ups-quoteless" for row in result.desk.cues)
    # Written again with the quote, it lands.
    landed = next(row for row in result.desk.cues if row.id == "push-ups-quoted")
    assert landed.quote == selection.quote
    assert landed.surface == CueSurface.on_demand
    assert result.mutated is True


async def test_an_ordinary_cue_still_needs_no_quote() -> None:
    """Only a selection has a phrase to carry. A correction from plain talk
    is not silently held to a field it cannot fill."""
    result = await _play(match_golden("поясница забирает нагрузку").utterance)
    add = next(call for call in result.tool_calls if call.name == "add_cue")
    assert add.ok is True
    assert add.error is None


# --- R6: one media on a cue, and only the person's own link ---------------


async def test_a_link_the_person_sent_rides_the_cue_unchanged() -> None:
    """Q33: she asked not to have to leave and search. The video she sent is
    attached to the step she asked about — behind the `?`, character for
    character, and nothing else is sourced for her."""
    golden = match_golden("вот видео с этим движением: https://youtu.be/9x1FZrq3kQo")
    assert golden is not None
    assert golden.id == "cue_with_link"
    assert golden.selection is not None
    result = await _play_golden(golden)
    assert result.mutated is True
    assert _names(result) == golden.expect.tools
    expected = golden.expect.cue
    assert expected is not None
    assert expected.media_url is not None
    cue = next(row for row in result.desk.cues if row.id == "push-ups-negatives-talk")
    assert cue.kind == CueKind.clarification
    # Media rides its cue's surface: a clarification sits behind the «?», and
    # rep one stays readable (04 Cue).
    assert cue.surface == CueSurface.on_demand
    assert cue.quote == golden.selection.quote
    assert cue.media is not None
    assert cue.media.kind == "link"
    assert cue.media.url == expected.media_url
    # The URL on the desk is the one out of her message, not one we tidied up.
    assert cue.media.url in golden.utterance
    # At most one item per cue — the field holds a single link, never a list.
    assert not isinstance(cue.media, list)
    # The do-time correction is untouched: media did not become a precondition
    # for doing the thing (04, «a step must be executable without its media»).
    brace = next(row for row in result.desk.cues if row.id == "push-ups-brace")
    assert brace.surface == CueSurface.do_time
    assert brace.media is None


async def test_an_invented_link_is_refused_and_the_desk_stays_clean() -> None:
    """06 #23's trap: a hallucinated URL on a movement is worse than none. The
    call comes back named, the desk never takes it, and the same turn writes
    the cue again — this time with no media at all."""
    golden = match_golden("как понять, что я делаю отжимания правильно?")
    assert golden is not None
    assert golden.id == "cue_link_invented"
    assert golden.expect.cue is not None
    assert golden.expect.cue.media_url is None
    result = await _play(golden.utterance)
    assert _names(result) == golden.expect.tools
    first, second = result.tool_calls
    assert first.ok is False
    assert first.error == MEDIA_NOT_IN_CONVERSATION
    assert first.arguments["media"]["url"] not in golden.utterance
    assert second.ok is True
    # The refused call left nothing behind.
    assert all(row.id != "push-ups-form-link-talk" for row in result.desk.cues)
    landed = next(row for row in result.desk.cues if row.id == "push-ups-form-talk")
    assert landed.media is None
    assert landed.surface == CueSurface.do_time
    # No URL reached the desk anywhere on this turn.
    assert all(row.media is None for row in result.desk.cues)
    assert result.mutated is True


# --- R1: the checklist is a practice, not a to-do list --------------------


async def test_checklist_shopping_lands_with_a_rhythm_and_a_do_time_cue() -> None:
    """Never-do #14 as a golden: the type only ships carrying both."""
    golden = match_golden("список покупок на неделю: хлеб, молоко, яблоки")
    assert golden is not None
    assert golden.id == "checklist_shopping"
    result = await _play(golden.utterance)
    names = _names(result)
    assert result.mutated is True
    assert names == golden.expect.tools
    for name in golden.expect.forbidden_tools:
        assert name not in names
    create = next(call for call in result.tool_calls if call.name == "create_widget")
    assert create.ok is True
    assert create.arguments["type"] == "checklist"
    widget = next(row for row in result.desk.widgets if row.subject_id == "groceries")
    assert widget.type == WidgetType.checklist
    assert [item.text for item in widget.payload.items or []] == ["хлеб", "молоко", "яблоки"]
    assert all(item.done is False for item in widget.payload.items or [])
    # Type owns the shape (never-do #8): a checklist is a 4×2, never an
    # unsized tile that would take the packer's default cell.
    assert widget.tile_size == "4x2"
    # The rhythm arrived in the same call — R0 holds for the new types too.
    assert golden.expect.cadence is not None
    groceries = _subject(result.desk, "groceries")
    assert groceries.cadence.period == golden.expect.cadence.period
    assert groceries.cadence.count == golden.expect.cadence.count
    # …and so did the do-time line the tile has to show at rep one (P9).
    expected = golden.expect.cue
    assert expected is not None
    cue = next(row for row in result.desk.cues if row.subject_id == "groceries")
    assert cue.kind == CueKind.correction
    assert cue.surface == CueSurface.do_time
    for needle in expected.text_contains:
        assert needle in cue.text
    assert cue.id in groceries.cue_ids


async def test_the_checklist_snapshot_is_a_picture_not_a_runtime() -> None:
    """A snapshot in the chat carries no tickable line (never-do #6)."""
    result = await _play("список покупок на неделю: хлеб, молоко, яблоки")
    card = next(row for row in result.snapshots if row.subject_id == "groceries")
    assert card.line.startswith("0 / 3")
    assert "после работы" in card.line
    assert not hasattr(card, "items")


async def test_a_new_practice_gets_no_hour_it_did_not_ask_for() -> None:
    """Same lock as the gym: a list is not a reason to hang a clock (В1.2)."""
    result = await _play("список покупок на неделю: хлеб, молоко, яблоки")
    assert "set_reminder" not in _names(result)
    reminders = [
        row
        for row in result.desk.widgets
        if row.subject_id == "groceries" and row.type == WidgetType.reminder
    ]
    assert reminders == []


# --- R1: the timer is a practice, not a stopwatch -------------------------


async def test_timer_meditation_lands_with_a_length_a_rhythm_and_a_cue() -> None:
    golden = match_golden("медитация 10 минут каждый день")
    assert golden is not None
    assert golden.id == "timer_meditation"
    result = await _play(golden.utterance)
    names = _names(result)
    assert result.mutated is True
    assert names == golden.expect.tools
    for name in golden.expect.forbidden_tools:
        assert name not in names
    widget = next(row for row in result.desk.widgets if row.subject_id == "meditation")
    assert widget.type == WidgetType.timer
    assert widget.payload.seconds == 600
    # A fresh timer stands still: nothing banked, no run going.
    assert widget.payload.elapsed == 0
    assert widget.payload.started_at is None
    assert widget.tile_size == "2x2"
    assert golden.expect.cadence is not None
    meditation = _subject(result.desk, "meditation")
    assert meditation.cadence.period == golden.expect.cadence.period
    assert meditation.cadence.count == golden.expect.cadence.count
    expected = golden.expect.cue
    assert expected is not None
    cue = next(row for row in result.desk.cues if row.subject_id == "meditation")
    assert cue.kind == CueKind.correction
    assert cue.surface == CueSurface.do_time
    for needle in expected.text_contains:
        assert needle in cue.text


async def test_the_timer_snapshot_is_a_picture_not_a_runtime() -> None:
    """The chat card shows the length and the cue — nothing that counts down."""
    result = await _play("медитация 10 минут каждый день")
    card = next(row for row in result.snapshots if row.subject_id == "meditation")
    assert card.line.startswith("10:00")
    assert "дыши носом" in card.line


# --- R1: the stepper, only when the person asked for takts ----------------


async def test_stepper_warmup_lands_with_beats_a_rhythm_and_a_cue() -> None:
    golden = match_golden("разминка по шагам, два раза в неделю")
    assert golden is not None
    assert golden.id == "stepper_warmup"
    result = await _play(golden.utterance)
    names = _names(result)
    assert result.mutated is True
    assert names == golden.expect.tools
    for name in golden.expect.forbidden_tools:
        assert name not in names
    widget = next(row for row in result.desk.widgets if row.subject_id == "warmup")
    assert widget.type == WidgetType.stepper
    assert widget.payload.beats == [
        "суставная разминка",
        "5 минут велотренажёра",
        "два подхода без веса",
    ]
    assert widget.payload.current == 0
    assert widget.tile_size == "4x2"
    assert golden.expect.cadence is not None
    warmup = _subject(result.desk, "warmup")
    assert warmup.cadence.period == golden.expect.cadence.period
    assert warmup.cadence.count == golden.expect.cadence.count
    expected = golden.expect.cue
    assert expected is not None
    cue = next(row for row in result.desk.cues if row.subject_id == "warmup")
    assert cue.kind == CueKind.correction
    assert cue.surface == CueSurface.do_time
    for needle in expected.text_contains:
        assert needle in cue.text


async def test_the_stepper_snapshot_is_a_picture_not_a_runtime() -> None:
    result = await _play("разминка по шагам, два раза в неделю")
    card = next(row for row in result.snapshots if row.subject_id == "warmup")
    assert card.line.startswith("1 / 3")
    assert "на холодную" in card.line


def test_a_plain_practice_is_not_written_as_a_stepper() -> None:
    """Q1: the stepper is for a subject that needs takts. «запиши зал» is a
    counter, and a golden that quietly upgraded it would teach the live model
    to reach for beats on anything."""
    for golden_id in ("gym_no_clock", "gym_no_clock_en", "checklist_shopping", "timer_meditation"):
        golden = next(row for row in load_goldens() if row.id == golden_id)
        types = [
            call.arguments.get("type")
            for turn in golden.scripted
            for call in turn.tool_calls
            if call.name == "create_widget"
        ]
        assert "stepper" not in types, golden_id
