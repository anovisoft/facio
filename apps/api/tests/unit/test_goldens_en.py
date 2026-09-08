"""English goldens: the same desk locks as the Russian set, on English utterances."""

from __future__ import annotations

from datetime import datetime, time

import pytest

from facio_domain.chips import MAX_CHIPS, weekday_chip
from facio_domain.desk import founding_desk
from facio_domain.models import CueKind, CueSurface, Desk, SubjectStatus, WidgetType
from facio_domain.tools import RUNNABLE_TYPES, apply_tool, times_per_week

from facio_api.providers.scripted import ScriptedProvider
from facio_api.providers.types import ModelToolCall, ModelTurn
from facio_api.talk.goldens import Golden, load_goldens, match_golden
from facio_api.talk.loop import MEDIA_NOT_IN_CONVERSATION, run_turn
from facio_api.talk.spec import SYSTEM_PROMPT
from facio_api.talk.schemas import TalkSelection, TalkTurnRequest

NOW = datetime(2026, 8, 15, 12, 0, 0)
FOUNDING_BRACE = "brace the core and the glutes"
FOUNDING_IDS = {"bike", "push-ups", "vegetables"}
UNKNOWN_EN = "quaxnuted probe 174"
RUSSIAN_IDS = {
    "cadence_shrink",
    "checklist_shopping",
    "clarification_orphan",
    "clarification_selection",
    "cue_link_invented",
    "cue_with_link",
    "drift_answer",
    "explain_only",
    "group_one_widget",
    "gym_no_clock",
    "gym_until_22",
    "hour_already_past",
    "lower_back",
    "method_4_to_30",
    "miss_skip",
    "named_hour_beats_closing",
    "pain_raise",
    "pain_skip_freeze",
    "remind_at_19",
    "search_back",
    "stepper_warmup",
    "thaw_pause",
    "timer_meditation",
    "upwork_hours",
}


def _request(utterance: str, selection: TalkSelection | None = None) -> TalkTurnRequest:
    return TalkTurnRequest(
        utterance=utterance,
        desk=founding_desk(now=NOW),
        thread=[],
        thread_id="golden-en",
        now=NOW,
        locale="en",
        selection=selection,
    )


async def _play(utterance: str, selection: TalkSelection | None = None):
    return await run_turn(
        _request(utterance, selection),
        ScriptedProvider.for_utterance(utterance),
        now=NOW,
    )


async def _play_golden(golden: Golden):
    """Replay a golden the way the client sends it — selection included."""
    return await _play(golden.utterance, golden.selection)


def _names(result) -> list[str]:
    return [call.name for call in result.tool_calls]


def _subject(desk: Desk, subject_id: str):
    return next(row for row in desk.subjects if row.id == subject_id)


def _sentences(text: str) -> list[str]:
    chunks = text.replace("!", ".").replace("?", ".").split(".")
    return [part.strip() for part in chunks if part.strip()]


def _needles(golden: Golden) -> list[str]:
    return [row.casefold() for row in (golden.match or [golden.utterance])]


# --- the set itself -------------------------------------------------------


def test_every_russian_golden_has_an_english_mirror() -> None:
    ids = {golden.id for golden in load_goldens()}
    assert {f"{row}_en" for row in RUSSIAN_IDS} <= ids


def test_english_goldens_carry_no_cyrillic_utterance() -> None:
    for golden in load_goldens():
        if not golden.id.endswith("_en"):
            continue
        blob = golden.utterance + "".join(golden.match)
        assert not any("Ѐ" <= char <= "ӿ" for char in blob), golden.id


def test_needles_never_overlap() -> None:
    """`match_golden` takes the first file by sorted name — needles must be disjoint."""
    goldens = load_goldens()
    clashes: list[tuple[str, str, str, str]] = []
    for left in goldens:
        for right in goldens:
            if left.id >= right.id:
                continue
            for a in _needles(left):
                for b in _needles(right):
                    if a in b or b in a:
                        clashes.append((left.id, a, right.id, b))
    assert clashes == []


@pytest.mark.parametrize("golden", load_goldens(), ids=lambda row: row.id)
def test_a_golden_that_creates_a_practice_names_its_rhythm(golden: Golden) -> None:
    """A new subject arrives with a cadence or it does not arrive ([06] #14)."""
    for turn in golden.scripted:
        for call in turn.tool_calls:
            if call.name != "create_widget":
                continue
            if call.arguments.get("subject_id") in FOUNDING_IDS:
                continue
            cadence = call.arguments.get("cadence")
            assert isinstance(cadence, dict), golden.id
            assert cadence.get("period") in {"day", "week", "none"}, golden.id


# Phrases that are never a human answer — they are our own rules and arithmetic
# read back to the person. The first lock of the prompt forbids exactly this.
RULE_LEAKS = (
    "не просил",
    "did not ask",
    "не трогаю",
    "leaving the hour alone",
    "окно само",
    "window itself",
    "не вычита",
    "not subtracting",
    "не новая команда",
    "not a new command",
    "не 20:00",
    "not 20:00",
)


@pytest.mark.parametrize("golden", load_goldens(), ids=lambda row: row.id)
def test_no_golden_reads_our_rules_back_to_the_person(golden: Golden) -> None:
    for turn in golden.scripted:
        text = (turn.text or "").casefold()
        leaked = [needle for needle in RULE_LEAKS if needle in text]
        assert leaked == [], f"{golden.id}: {leaked}"


@pytest.mark.parametrize("golden", load_goldens(), ids=lambda row: row.id)
def test_each_utterance_and_needle_routes_home(golden: Golden) -> None:
    assert match_golden(golden.utterance) is not None
    assert match_golden(golden.utterance).id == golden.id
    for needle in golden.match or [golden.utterance]:
        matched = match_golden(needle)
        assert matched is not None
        assert matched.id == golden.id


async def test_unknown_english_utterance_stays_text_only() -> None:
    assert match_golden(UNKNOWN_EN) is None
    result = await _play(UNKNOWN_EN)
    assert result.mutated is False
    assert result.tool_calls == []
    assert result.snapshots == []


# --- founding three -------------------------------------------------------


async def test_lower_back_en_writes_do_time_cue() -> None:
    golden = match_golden("my lower back takes the load")
    assert golden is not None
    assert golden.id == "lower_back_en"
    result = await _play(golden.utterance)
    assert result.mutated is True
    assert _names(result) == golden.expect.tools
    cue = next(row for row in result.desk.cues if row.subject_id == "push-ups" and row.id.endswith("en-talk"))
    assert cue.surface == CueSurface.do_time
    for needle in golden.expect.cue.text_contains if golden.expect.cue else []:
        assert needle in cue.text
    assert result.snapshots
    assert result.snapshots[0].widget_id == "push-ups-counter"


async def test_pain_raise_en_does_not_lift_target() -> None:
    golden = match_golden("it hurts, let's do 40")
    assert golden is not None
    assert golden.id == "pain_raise_en"
    result = await _play(golden.utterance)
    assert _names(result) == golden.expect.tools
    assert result.tool_calls[0].ok is False
    assert result.tool_calls[0].error == "pain_forbids_raise"
    goal = next(row.target.goal for row in result.desk.subjects if row.id == "push-ups")
    assert goal <= (golden.expect.target_goal_max or 30)
    assert any(call.name == "add_cue" and call.ok for call in result.tool_calls)


async def test_explain_only_en_has_no_card() -> None:
    golden = match_golden("what does keeping the core tight mean?")
    assert golden is not None
    assert golden.id == "explain_only_en"
    result = await _play(golden.utterance)
    assert result.mutated is False
    assert result.snapshots == []
    assert result.tool_calls == []
    assert result.text


# --- В1.2 six -------------------------------------------------------------


async def test_method_4_to_30_en_writes_current_and_cue() -> None:
    golden = match_golden("I can do 4, I want 30 in a row, how?")
    assert golden is not None
    assert golden.id == "method_4_to_30_en"
    result = await _play(golden.utterance)
    names = _names(result)
    assert result.mutated is True
    assert names[0] in {"list_desk", "get_widget", "get_subject"}
    assert "update_widget" in names
    assert "add_cue" in names
    for name in golden.expect.forbidden_tools:
        assert name not in names
    update = next(call for call in result.tool_calls if call.name == "update_widget")
    assert update.arguments["widget_id"] == "push-ups-counter"
    assert update.arguments["target"] == 30
    assert update.arguments["count"] == 4
    push = _subject(result.desk, "push-ups")
    assert push.target is not None
    assert push.target.current == 4
    assert push.target.goal == 30
    assert times_per_week(push.cadence) <= 3
    cue = next(row for row in result.desk.cues if row.subject_id == "push-ups" and row.id.endswith("en-talk"))
    assert cue.surface == CueSurface.do_time
    # The method changes *how* it is done: correction at do-time, not an
    # explanation filed behind a «?» ([04] Cue defaults).
    assert golden.expect.cue is not None
    assert golden.expect.cue.kind == "correction"
    assert cue.kind == CueKind.correction
    assert cue.text != FOUNDING_BRACE
    for needle in golden.expect.cue.text_contains if golden.expect.cue else []:
        assert needle in cue.text
    assert any(card.widget_id == "push-ups-counter" for card in result.snapshots)
    assert len(_sentences(result.text)) >= 2


async def test_gym_no_clock_en_creates_counter_without_reminder() -> None:
    golden = match_golden("put the gym on the desk")
    assert golden is not None
    assert golden.id == "gym_no_clock_en"
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
    assert golden.expect.cadence is not None
    assert create.arguments["cadence"]["period"] == golden.expect.cadence.period
    gym = _subject(result.desk, subject_id)
    assert gym.cadence.period == golden.expect.cadence.period
    assert gym.cadence.count == golden.expect.cadence.count
    assert times_per_week(gym.cadence) >= 1
    bike = _subject(result.desk, "bike")
    assert bike.window is not None
    assert bike.window.latest_by == time(19, 0)


async def test_miss_skip_en_does_not_hang_a_clock() -> None:
    golden = match_golden("didn't go today")
    assert golden is not None
    assert golden.id == "miss_skip_en"
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


async def test_remind_at_19_en_uses_stated_hour() -> None:
    golden = match_golden("remind me at 19, I am asleep by 21")
    assert golden is not None
    assert golden.id == "remind_at_19_en"
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
        row for row in result.desk.cues if row.subject_id == "bike" and row.surface == CueSurface.timing
    ]
    assert any("asleep" in row.text.casefold() for row in timing)
    assert "add_cue" in names


async def test_gym_until_22_en_is_arithmetic() -> None:
    golden = match_golden("the gym shuts at 22")
    assert golden is not None
    assert golden.id == "gym_until_22_en"
    result = await _play(golden.utterance)
    assert result.mutated is True
    reminder = next(call for call in result.tool_calls if call.name == "set_reminder")
    assert reminder.arguments["closes_at"] in {"22:00", "22:00:00"}
    assert "latest_by" not in reminder.arguments
    bike = _subject(result.desk, "bike")
    assert bike.window is not None
    assert bike.window.latest_by == time(19, 0)
    assert bike.window.closes_at == time(22, 0)


async def test_named_hour_beats_closing_en_formula() -> None:
    golden = match_golden("by 23 it already closes. Remind me to go to the gym at 19")
    assert golden is not None
    assert golden.id == "named_hour_beats_closing_en"
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


async def test_cadence_shrink_en_does_not_raise_goal() -> None:
    golden = match_golden("make it once a week")
    assert golden is not None
    assert golden.id == "cadence_shrink_en"
    result = await _play(golden.utterance)
    names = _names(result)
    assert result.mutated is True
    assert names[0] in {"shrink_subject", "set_cadence"}
    shrink = next(call for call in result.tool_calls if call.name == "shrink_subject")
    assert shrink.arguments["subject_id"] == "push-ups"
    push = _subject(result.desk, "push-ups")
    assert times_per_week(push.cadence) <= 1
    assert push.target is not None
    assert push.target.goal <= 30


# --- В2.3 freeze / thaw ---------------------------------------------------


async def test_pain_skip_freeze_en_pauses_bike_without_raising() -> None:
    golden = match_golden("skipped today, my back hurt")
    assert golden is not None
    assert golden.id == "pain_skip_freeze_en"
    assert "didn't go today" not in golden.utterance
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


def test_match_thaw_phrases_en() -> None:
    assert match_golden("it eased off").id == "thaw_pause_en"
    assert match_golden("the back is fine now").id == "thaw_pause_en"
    assert match_golden("bring the bike back").id == "thaw_pause_en"


async def test_thaw_pause_en_restores_bike() -> None:
    golden = match_golden("it eased off")
    assert golden is not None
    assert golden.id == "thaw_pause_en"
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
            thread_id="golden-en",
            now=NOW,
            locale="en",
        ),
        ScriptedProvider.for_utterance(golden.utterance),
        now=NOW,
    )
    assert result.mutated is True
    assert _names(result) == golden.expect.tools
    bike = _subject(result.desk, "bike")
    assert bike.status == SubjectStatus.active
    assert bike.paused_at is None


# --- R3 selection → clarification ----------------------------------------


async def test_clarification_selection_en_lands_on_demand_with_the_quote() -> None:
    golden = match_golden("what does this mean: don't let the hips sag?")
    assert golden is not None
    assert golden.id == "clarification_selection_en"
    assert golden.selection is not None
    result = await _play_golden(golden)
    assert result.mutated is True
    assert _names(result) == golden.expect.tools
    expected = golden.expect.cue
    assert expected is not None
    cue = next(row for row in result.desk.cues if row.id == "push-ups-hips-en-talk")
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
    brace = next(row for row in result.desk.cues if row.id == "push-ups-brace")
    assert brace.surface == CueSurface.do_time


async def test_clarification_orphan_en_stays_text_only() -> None:
    golden = match_golden("what does this mean: running economy?")
    assert golden is not None
    assert golden.id == "clarification_orphan_en"
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


# --- R6: one media on a cue, and only the person's own link ---------------


async def test_a_link_the_person_sent_rides_the_cue_unchanged_en() -> None:
    """The English half of Q33: her video, her step, character for character."""
    golden = match_golden("here is a video of that movement: https://youtu.be/7bK2mZq1Rf4")
    assert golden is not None
    assert golden.id == "cue_with_link_en"
    assert golden.selection is not None
    result = await _play_golden(golden)
    assert result.mutated is True
    assert _names(result) == golden.expect.tools
    expected = golden.expect.cue
    assert expected is not None
    assert expected.media_url is not None
    cue = next(row for row in result.desk.cues if row.id == "push-ups-negatives-en-talk")
    assert cue.kind == CueKind.clarification
    # Media rides its cue's surface: behind the «?», never inline at do-time (04).
    assert cue.surface == CueSurface.on_demand
    assert cue.quote == golden.selection.quote
    assert cue.media is not None
    assert cue.media.kind == "link"
    assert cue.media.url == expected.media_url
    assert cue.media.url in golden.utterance
    brace = next(row for row in result.desk.cues if row.id == "push-ups-brace")
    assert brace.surface == CueSurface.do_time
    assert brace.media is None


async def test_an_invented_link_is_refused_and_the_desk_stays_clean_en() -> None:
    """Same lock on the English half: a URL nobody wrote never reaches the desk."""
    golden = match_golden("how do I know I am doing push-ups right?")
    assert golden is not None
    assert golden.id == "cue_link_invented_en"
    assert golden.expect.cue is not None
    assert golden.expect.cue.media_url is None
    result = await _play(golden.utterance)
    assert _names(result) == golden.expect.tools
    first, second = result.tool_calls
    assert first.ok is False
    assert first.error == MEDIA_NOT_IN_CONVERSATION
    assert first.arguments["media"]["url"] not in golden.utterance
    assert second.ok is True
    assert all(row.id != "push-ups-form-link-en-talk" for row in result.desk.cues)
    landed = next(row for row in result.desk.cues if row.id == "push-ups-form-en-talk")
    assert landed.media is None
    assert landed.surface == CueSurface.do_time
    assert all(row.media is None for row in result.desk.cues)
    assert result.mutated is True


def test_the_media_bullet_is_bilingual_and_refuses_rather_than_asks() -> None:
    """A wish is not a lock: the bullet names the refusal, and it says in both
    halves that nothing is searched for or supplied on the person's behalf
    ([06] #23 and its trap table)."""
    bullet = next(
        row for row in SYSTEM_PROMPT.splitlines() if row.startswith("- Media on a cue")
    )
    assert "media_not_in_conversation" in bullet
    assert "character for character" in bullet
    assert "At most one item" in bullet
    assert "вот видео" in bullet
    assert "here is a video" in bullet
    for needle in ("Do not search for a video", "do not offer one of yours"):
        assert needle in bullet, needle
    # No library, no catalogue: the only photo is the person's own.
    assert "kind photo, ref" in bullet


# --- R4: the answer to drift only ever goes down ---------------------------


async def test_drift_answer_en_offers_less_and_never_more() -> None:
    """Same lock as the Russian half: a quiet practice is never answered with
    a bigger number ([06] #21). The offer shrinks or nothing happens."""
    golden = match_golden("the bike has been sitting for three weeks, what now?")
    assert golden is not None
    assert golden.id == "drift_answer_en"
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
    push = _subject(result.desk, "push-ups")
    assert push.target is not None
    assert push.target.goal <= (golden.expect.target_goal_max or 30)


async def test_drift_answer_en_says_nothing_about_trying_harder() -> None:
    result = await _play("the bike has been sitting for three weeks, what now?")
    lowered = result.text.casefold()
    for needle in ("try harder", "catch up", "make up for", "drift"):
        assert needle not in lowered, needle


def test_the_drift_prompt_keeps_the_ladder_with_the_law() -> None:
    """The model wording one morning line is fine; the model deciding whether
    there is drift, which rung it is, or that the answer is «more» is not
    ([06] AI #10, #21). Both halves of the bilingual bullet say so."""
    rows = [row for row in SYSTEM_PROMPT.splitlines() if row.startswith("- ")]
    ladder = next(row for row in rows if "Drift belongs to the desk" in row)
    assert "set_cadence week count 1" in ladder
    assert "shrink_subject" in ladder
    assert "retire_subject" in ladder
    forbidden = next(row for row in rows if "bigger number is the one forbidden move" in row)
    for needle in ("постарайся", "try harder", "наверстай", "catch up"):
        assert needle in forbidden, needle


# --- R4 addendum: the quote has to reach the cue ---------------------------


def test_the_selection_bullet_demands_the_quote_in_both_halves() -> None:
    """R3-B measured the live failure: surface right, `quote` empty. The bullet
    now names the requirement and the refusal in both languages."""
    bullet = next(
        row for row in SYSTEM_PROMPT.splitlines() if row.startswith("- A selected phrase")
    )
    assert "quote is required here" in bullet
    assert "character for character" in bullet
    assert "quote_required" in bullet
    assert "не роняй таз" in bullet
    assert "don't let the hips sag" in bullet
    for needle in ("never a paraphrase", "never shortened", "never empty"):
        assert needle in bullet, needle


async def test_english_selection_without_a_quote_is_refused_too() -> None:
    selection = TalkSelection(
        quote="don't let the hips sag", widget_id="push-ups-counter", step_id="rep-1"
    )
    result = await run_turn(
        TalkTurnRequest(
            utterance="what does this mean?",
            desk=founding_desk(now=NOW),
            thread=[],
            thread_id="golden-en",
            now=NOW,
            locale="en",
            selection=selection,
        ),
        QuotelessProviderEN(),
        now=NOW,
    )
    first = result.tool_calls[0]
    assert first.name == "add_cue"
    assert first.ok is False
    assert first.error == "quote_required"
    landed = next(row for row in result.desk.cues if row.id == "push-ups-quoted-en")
    assert landed.quote == selection.quote


class QuotelessProviderEN:
    """The R3-B failure on the English half: a clarification with no phrase."""

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
            "text": "keep the hips in line with the shoulders and heels",
        }
        if self._round == 1:
            return ModelTurn(
                tool_calls=[
                    ModelToolCall(id="c1", name="add_cue", arguments={"id": "push-ups-quoteless-en", **base})
                ]
            )
        if self._round == 2:
            return ModelTurn(
                tool_calls=[
                    ModelToolCall(
                        id="c2",
                        name="add_cue",
                        arguments={"id": "push-ups-quoted-en", **base, "quote": "don't let the hips sag"},
                    )
                ]
            )
        return ModelTurn(text="Keep the hips in one line with the shoulders and heels.")


# --- R1: the checklist, in English ---------------------------------------


async def test_checklist_shopping_en_lands_with_a_rhythm_and_a_do_time_cue() -> None:
    golden = match_golden("shopping list for the week: bread, milk, apples")
    assert golden is not None
    assert golden.id == "checklist_shopping_en"
    result = await _play(golden.utterance)
    names = _names(result)
    assert result.mutated is True
    assert names == golden.expect.tools
    for name in golden.expect.forbidden_tools:
        assert name not in names
    widget = next(row for row in result.desk.widgets if row.subject_id == "groceries")
    assert widget.type == WidgetType.checklist
    assert [item.text for item in widget.payload.items or []] == ["bread", "milk", "apples"]
    assert widget.tile_size == "4x2"
    assert golden.expect.cadence is not None
    groceries = _subject(result.desk, "groceries")
    assert groceries.cadence.period == golden.expect.cadence.period
    assert groceries.cadence.count == golden.expect.cadence.count
    expected = golden.expect.cue
    assert expected is not None
    cue = next(row for row in result.desk.cues if row.subject_id == "groceries")
    assert cue.kind == CueKind.correction
    assert cue.surface == CueSurface.do_time
    for needle in expected.text_contains:
        assert needle in cue.text
    # The English turn answers in English — cue text follows the person.
    assert not any("\u0400" <= char <= "\u04ff" for char in cue.text)
    assert not any("\u0400" <= char <= "\u04ff" for char in result.text)


def test_the_prompt_offers_exactly_the_types_that_have_a_runtime() -> None:
    """The last bullet is the catalog lock, and it tracks the gate rather than
    a hand-kept list: a type is advertised as placeable only once `apply_tool`
    will actually let it land (never-do #14). Advertising one that is still
    refused would spend a whole turn on a call that cannot work."""
    rows = [row for row in SYSTEM_PROMPT.splitlines() if row.startswith("- ")]
    catalog = rows[-1]
    assert catalog.startswith("- Widget type only from the catalog")
    for widget_type in WidgetType:
        named = widget_type.value in catalog
        assert named is (widget_type in RUNNABLE_TYPES), widget_type.value
    assert any("rhythm" in row and "do-time" in row for row in rows)


# --- R1: the timer, in English -------------------------------------------


async def test_timer_meditation_en_lands_with_a_length_a_rhythm_and_a_cue() -> None:
    golden = match_golden("meditate 10 minutes every day")
    assert golden is not None
    assert golden.id == "timer_meditation_en"
    result = await _play(golden.utterance)
    names = _names(result)
    assert result.mutated is True
    assert names == golden.expect.tools
    for name in golden.expect.forbidden_tools:
        assert name not in names
    widget = next(row for row in result.desk.widgets if row.subject_id == "meditation")
    assert widget.type == WidgetType.timer
    assert widget.payload.seconds == 600
    assert widget.tile_size == "2x2"
    assert golden.expect.cadence is not None
    meditation = _subject(result.desk, "meditation")
    assert meditation.cadence.period == golden.expect.cadence.period
    assert meditation.cadence.count == golden.expect.cadence.count
    expected = golden.expect.cue
    assert expected is not None
    cue = next(row for row in result.desk.cues if row.subject_id == "meditation")
    assert cue.surface == CueSurface.do_time
    for needle in expected.text_contains:
        assert needle in cue.text
    assert not any("\u0400" <= char <= "\u04ff" for char in cue.text)
    assert not any("\u0400" <= char <= "\u04ff" for char in result.text)


# --- R1: the stepper, in English -----------------------------------------


async def test_stepper_warmup_en_lands_with_beats_a_rhythm_and_a_cue() -> None:
    golden = match_golden("walk me through the warm-up step by step, twice a week")
    assert golden is not None
    assert golden.id == "stepper_warmup_en"
    result = await _play(golden.utterance)
    names = _names(result)
    assert result.mutated is True
    assert names == golden.expect.tools
    for name in golden.expect.forbidden_tools:
        assert name not in names
    widget = next(row for row in result.desk.widgets if row.subject_id == "warmup")
    assert widget.type == WidgetType.stepper
    assert widget.payload.beats == ["joint circles", "5 minutes on the bike", "two sets with no weight"]
    assert widget.payload.current == 0
    assert widget.tile_size == "4x2"
    assert golden.expect.cadence is not None
    warmup = _subject(result.desk, "warmup")
    assert warmup.cadence.count == golden.expect.cadence.count
    cue = next(row for row in result.desk.cues if row.subject_id == "warmup")
    assert cue.surface == CueSurface.do_time
    assert not any("\u0400" <= char <= "\u04ff" for char in cue.text)
    assert not any("\u0400" <= char <= "\u04ff" for char in result.text)


def test_every_placed_type_is_one_the_desk_will_accept() -> None:
    """A golden that places a type `apply_tool` refuses would be a green test
    over a turn that cannot work on a real desk (never-do #14)."""
    for golden in load_goldens():
        for turn in golden.scripted:
            for call in turn.tool_calls:
                if call.name != "create_widget":
                    continue
                placed = WidgetType(call.arguments["type"])
                assert placed in RUNNABLE_TYPES, f"{golden.id}: {placed.value}"


async def test_one_widget_en_is_answered_not_silently_agreed() -> None:
    """The English half of the same lock: already one tile, said out loud."""
    golden = match_golden("can you put them in one widget?")
    assert golden is not None
    assert golden.id == "group_one_widget_en"
    result = await _play(golden.utterance)
    assert result.mutated is False
    assert result.tool_calls == []
    assert result.snapshots == []
    assert result.text
    lowered = result.text.casefold()
    assert "already" in lowered
    assert "tile" in lowered


async def test_upwork_en_seven_hours_land_as_one_window_and_seven_checks() -> None:
    """The same Q34 lock on the English reply."""
    golden = match_golden(
        "remind me every day at 10, 12, 15, 16:30, 18, 21, 22 to check Upwork,"
        " and a checkbox for each check"
    )
    assert golden is not None
    assert golden.id == "upwork_hours_en"
    result = await _play(golden.utterance)
    assert result.mutated is True
    assert _names(result) == golden.expect.tools
    upwork = _subject(result.desk, "upwork")
    assert (upwork.cadence.count, upwork.cadence.period) == (7, "day")
    assert upwork.window is not None
    assert len(upwork.window.hours) == 7
    assert upwork.window.hours[0] == time(10, 0)
    assert upwork.window.latest_by == time(10, 0)
    cue = next(row for row in result.desk.cues if row.subject_id == "upwork")
    assert cue.surface == CueSurface.do_time
    assert not any("Ѐ" <= char <= "ӿ" for char in cue.text)
    assert not any("Ѐ" <= char <= "ӿ" for char in result.text)


# --- В3.3: the same lookup, in English -------------------------------------


async def test_search_back_en_finds_the_old_cue_and_does_not_lift_the_goal() -> None:
    """The founding turn writes the line; a later turn asks about it and finds
    it. Reading the person's own cues — not a catalogue, not the internet
    (never-do #23) — and reading changes nothing on the desk."""
    written = await _play("my lower back takes the load")
    assert written.mutated is True
    golden = match_golden("what did we write down about my lower back?")
    assert golden is not None
    assert golden.id == "search_back_en"
    before = written.desk.model_copy(deep=True)
    result = await run_turn(
        TalkTurnRequest(
            utterance=golden.utterance,
            desk=written.desk,
            thread=[],
            thread_id="golden-en",
            now=NOW,
            locale="en",
        ),
        ScriptedProvider.for_utterance(golden.utterance),
        now=NOW,
    )
    assert _names(result) == golden.expect.tools == ["search_facts"]
    assert result.tool_calls[0].ok is True
    assert result.mutated is False
    assert result.snapshots == []
    assert result.desk == before
    for name in golden.expect.forbidden_tools:
        assert name not in _names(result)
    push = _subject(result.desk, "push-ups")
    assert push.target is not None
    assert push.target.goal == golden.expect.target_goal_max == 30
    assert FOUNDING_BRACE in result.text
    assert not any("Ѐ" <= char <= "ӿ" for char in result.text)


def test_the_search_reads_english_cues_the_same_way() -> None:
    outcome = apply_tool(
        founding_desk(now=NOW),
        "add_cue",
        {
            "id": "push-ups-brace-en-talk",
            "subject_id": "push-ups",
            "kind": "correction",
            "text": "brace the core and the glutes, not the lower back",
            "surface": "do-time",
        },
        pain=False,
        now=NOW,
    )
    found = apply_tool(outcome.desk, "search_facts", {"query": "lower back"}, pain=False, now=NOW)
    assert found.ok is True
    assert [row["cue_id"] for row in found.data["facts"]] == ["push-ups-brace-en-talk"]
    assert found.desk == outcome.desk


def test_the_search_bullet_is_bilingual_and_never_invents_a_fact() -> None:
    """Both halves of the one English bullet: look before asking again, quote
    what was found, and say plainly when nothing was."""
    bullet = next(
        row for row in SYSTEM_PROMPT.splitlines() if row.startswith("- What they already told you")
    )
    assert "search_facts" in bullet
    assert "поясница" in bullet
    assert "lower back" in bullet
    for needle in ("there is nothing written", "never fill that silence", "only reads"):
        assert needle in bullet, needle


LATE = datetime(2026, 8, 15, 21, 0, 0)
TOMORROW_EN = "Remind me tomorrow"


def _late_request(utterance: str) -> TalkTurnRequest:
    return TalkTurnRequest(
        utterance=utterance,
        desk=founding_desk(now=NOW),
        thread=[],
        thread_id="golden-en",
        now=LATE,
        locale="en",
    )


async def test_an_hour_already_behind_us_is_said_out_loud_with_a_chip_en() -> None:
    golden = match_golden("set a reminder for 19:00")
    assert golden is not None
    assert golden.id == "hour_already_past_en"
    result = await run_turn(
        _late_request(golden.utterance),
        ScriptedProvider.for_utterance(golden.utterance),
        now=LATE,
    )
    assert _names(result) == golden.expect.tools
    assert result.reply_chips == golden.expect.chips == [TOMORROW_EN]
    assert result.mutated is True
    bike = _subject(result.desk, "bike")
    assert bike.window is not None
    assert bike.window.hours == [time(19, 0)]
    assert bike.cadence.count == 2
    assert _subject(result.desk, "push-ups").target.goal == 30


def test_the_chip_row_is_written_in_the_language_of_the_answer() -> None:
    """Not an English original translated on the client: a chip is a sentence
    the person is about to say (03). The two rows are written independently."""
    russian = match_golden("поставь напоминание на 19 часов")
    english = match_golden("set a reminder for 19:00")
    assert _chips_of(russian) == ["Напомни завтра"]
    assert _chips_of(english) == [TOMORROW_EN]
    assert not any("Ѐ" <= char <= "ӿ" for chip in _chips_of(english) for char in chip)


def _chips_of(golden: Golden) -> list[str]:
    for turn in golden.scripted:
        for call in turn.tool_calls:
            if call.name == "offer_chips":
                return list(call.arguments["chips"])
    return []


def test_the_chip_bullet_is_bilingual_and_never_offers_more() -> None:
    bullet = next(row for row in SYSTEM_PROMPT.splitlines() if row.startswith("- Something the desk cannot decide"))
    assert "offer_chips" in bullet
    assert "1–3" in bullet
    # The two example rows are the ones the naming table actually produces, so
    # the prompt cannot drift away from what a chip is allowed to say.
    assert weekday_chip([0, 2, 4], "ru") in bullet
    assert weekday_chip([0, 2, 4], "en") in bullet
    for needle in ("equal to or smaller", "try harder", "decides nothing"):
        assert needle in bullet, needle


@pytest.mark.parametrize("golden", load_goldens(), ids=lambda row: row.id)
def test_no_golden_offers_a_fourth_chip(golden: Golden) -> None:
    """One to three, never a fourth — a row that grows into a menu is a form."""
    for turn in golden.scripted:
        for call in turn.tool_calls:
            if call.name != "offer_chips":
                continue
            chips = call.arguments["chips"]
            assert 1 <= len(chips) <= MAX_CHIPS, golden.id
            assert len(set(chips)) == len(chips), golden.id
