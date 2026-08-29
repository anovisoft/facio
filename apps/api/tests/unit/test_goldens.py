from __future__ import annotations

from datetime import datetime, time

from facio_domain.desk import founding_desk
from facio_domain.models import CueKind, CueSurface, Desk, SubjectStatus, WidgetType
from facio_domain.tools import apply_tool, times_per_week

from facio_api.providers.scripted import ScriptedProvider
from facio_api.talk.goldens import load_goldens, match_golden
from facio_api.talk.loop import run_turn
from facio_api.talk.schemas import TalkTurnRequest

NOW = datetime(2026, 8, 15, 12, 0, 0)
SEED_BRACE = "держи корпус и ягодицы"
FOUNDING_IDS = {"bike", "push-ups", "vegetables"}


def _request(utterance: str) -> TalkTurnRequest:
    return TalkTurnRequest(
        utterance=utterance,
        desk=founding_desk(now=NOW),
        thread=[],
        thread_id="golden",
        now=NOW,
    )


async def _play(utterance: str):
    return await run_turn(_request(utterance), ScriptedProvider.for_utterance(utterance), now=NOW)


def _names(result) -> list[str]:
    return [call.name for call in result.tool_calls]


def _subject(desk: Desk, subject_id: str):
    return next(row for row in desk.subjects if row.id == subject_id)


def _sentences(text: str) -> list[str]:
    chunks = text.replace("!", ".").replace("?", ".").split(".")
    return [part.strip() for part in chunks if part.strip()]


RUSSIAN_IDS = {
    "cadence_shrink",
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
    "thaw_pause",
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
