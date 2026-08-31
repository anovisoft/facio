"""Desk invariants against a live vendor. Not golden tool sequences or verbatim text."""

from __future__ import annotations

from datetime import datetime, time

import pytest

from facio_domain.desk import founding_desk
from facio_domain.models import CueKind, CueSurface, Desk, SubjectStatus, WidgetType
from facio_domain.tools import times_per_week

from facio_api.talk.loop import MEDIA_NOT_IN_CONVERSATION
from facio_api.talk.schemas import TalkSelection, TalkTurnResponse, ThreadMessage

pytestmark = pytest.mark.live

SEED_BRACE = "держи корпус и ягодицы"
FOUNDING_BRACE = "brace the core and the glutes"
FOUNDING_IDS = {"bike", "push-ups", "vegetables"}
FOUNDING_PUSH_WEEKLY = 3.0
FOUNDING_PUSH_GOAL = 30
NOW = datetime(2026, 8, 15, 12, 0, 0)


def _names(result: TalkTurnResponse) -> list[str]:
    return [call.name for call in result.tool_calls]


def _subject(desk: Desk, subject_id: str):
    return next(row for row in desk.subjects if row.id == subject_id)


def _hhmm(value: object) -> tuple[int, int] | None:
    if value is None:
        return None
    if isinstance(value, time):
        return (value.hour, value.minute)
    text = str(value).strip()
    parts = text.split(":")
    if not parts or not parts[0].isdigit():
        return None
    hour = int(parts[0])
    minute = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
    return (hour, minute)


async def test_method_4_to_30_lands_current_and_cue(live_play) -> None:
    result = await live_play("могу 4, хочу 30 подряд, как?")
    names = _names(result)
    assert result.mutated is True
    assert "set_reminder" not in names
    push = _subject(result.desk, "push-ups")
    assert push.target is not None
    assert push.target.current == 4
    assert push.target.goal == 30
    assert times_per_week(push.cadence) <= FOUNDING_PUSH_WEEKLY
    method_cues = [
        row
        for row in result.desk.cues
        if row.subject_id == "push-ups"
        and row.surface == CueSurface.do_time
        and row.text != SEED_BRACE
        and row.text != FOUNDING_BRACE
    ]
    # The progression changes how it is done — a correction seen at rep one, not
    # a clarification filed behind a «?» ([04] Cue defaults).
    assert method_cues
    assert all(row.kind == CueKind.correction for row in method_cues)
    assert result.snapshots
    assert result.text


async def test_gym_no_clock_creates_counter_without_reminder(live_play) -> None:
    result = await live_play("запиши зал")
    names = _names(result)
    assert result.mutated is True
    assert "set_reminder" not in names
    creates = [
        call
        for call in result.tool_calls
        if call.name == "create_widget"
        and call.ok
        and call.arguments.get("type") == "counter"
        and call.arguments.get("subject_id") not in FOUNDING_IDS
    ]
    # A refusal leaves the desk untouched, so only a call that landed counts.
    assert creates, [(call.name, call.error) for call in result.tool_calls]
    create = creates[-1]
    subject_id = create.arguments["subject_id"]
    reminders = [
        row for row in result.desk.widgets if row.subject_id == subject_id and row.type == WidgetType.reminder
    ]
    assert reminders == []
    # A new practice arrives with a rhythm named in the same call ([06] #14).
    # `none` is legal for a one-off; a gym is not one.
    assert isinstance(create.arguments.get("cadence"), dict), create.arguments
    gym = _subject(result.desk, subject_id)
    assert gym.cadence.period in {"day", "week"}, gym.cadence
    assert times_per_week(gym.cadence) >= 1
    bike = _subject(result.desk, "bike")
    assert bike.window is not None
    assert bike.window.latest_by == time(19, 0)
    assert any(row.id == "bike-reminder" for row in result.desk.widgets)


async def test_miss_skip_does_not_hang_a_clock(live_play) -> None:
    result = await live_play("сегодня не сходил")
    names = _names(result)
    assert result.mutated is True
    assert any(call.name == "skip" and call.ok for call in result.tool_calls)
    assert "set_reminder" not in names
    bike = _subject(result.desk, "bike")
    assert bike.window is not None
    assert bike.window.latest_by == time(19, 0)


async def test_remind_at_19_uses_stated_hour(live_play) -> None:
    result = await live_play("напомни в 19, в 21 я уже сплю")
    names = _names(result)
    assert result.mutated is True
    for call in result.tool_calls:
        if call.name != "set_reminder":
            continue
        assert _hhmm(call.arguments.get("closes_at")) != (21, 0)
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


async def test_gym_until_22_is_arithmetic(live_play) -> None:
    result = await live_play("зал до 22")
    assert result.mutated is True
    reminder = next(
        call
        for call in result.tool_calls
        if call.name == "set_reminder" and _hhmm(call.arguments.get("closes_at")) == (22, 0)
    )
    assert _hhmm(reminder.arguments.get("latest_by")) != (19, 0)
    bike = _subject(result.desk, "bike")
    assert bike.window is not None
    assert bike.window.closes_at == time(22, 0)
    assert bike.window.latest_by == time(19, 0)


NAMED_HOUR_AND_DOOR = (
    "Хочу пойти в зал, но постоянно забываю про него и к 23 он уже закрывается. "
    "Напоминай мне о том что мне нужно пойти в зал в 19 часов"
)


async def test_named_hour_beats_closing_formula(live_play) -> None:
    result = await live_play(NAMED_HOUR_AND_DOOR)
    assert result.mutated is True
    reminder = next(call for call in result.tool_calls if call.name == "set_reminder")
    assert _hhmm(reminder.arguments.get("latest_by")) == (19, 0)
    assert _hhmm(reminder.arguments.get("latest_by")) != (20, 0)
    subject = _subject(result.desk, str(reminder.arguments["subject_id"]))
    assert subject.window is not None
    assert subject.window.latest_by == time(19, 0)
    assert subject.window.latest_by != time(20, 0)
    fires = [
        row.payload.fire_at
        for row in result.desk.widgets
        if row.subject_id == subject.id and row.type == WidgetType.reminder
    ]
    assert fires and fires[0] is not None
    assert fires[0].hour == 19


async def test_cadence_shrink_does_not_raise_goal(live_play) -> None:
    result = await live_play("давай раз в неделю")
    assert result.mutated is True
    push = _subject(result.desk, "push-ups")
    assert times_per_week(push.cadence) <= 1
    assert push.target is not None
    assert push.target.goal <= FOUNDING_PUSH_GOAL


async def test_pain_does_not_raise_goal_or_cadence(live_play) -> None:
    result = await live_play("больно, давай 40")
    push = _subject(result.desk, "push-ups")
    assert push.target is not None
    assert push.target.goal <= FOUNDING_PUSH_GOAL
    assert times_per_week(push.cadence) <= FOUNDING_PUSH_WEEKLY
    for call in result.tool_calls:
        if call.name == "update_widget":
            target = call.arguments.get("target")
            if target is not None and int(target) > FOUNDING_PUSH_GOAL:
                assert call.ok is False
        elif call.name == "set_cadence":
            count = call.arguments.get("count")
            period = call.arguments.get("period", "week")
            if count is None:
                continue
            weekly = float(count) * 7 if period == "day" else float(count)
            if weekly > FOUNDING_PUSH_WEEKLY:
                assert call.ok is False


async def test_pain_skip_freezes_bike_without_raising_goal(live_play) -> None:
    result = await live_play("сегодня пропустил, спина болела")
    bike = _subject(result.desk, "bike")
    assert bike.status == SubjectStatus.paused
    push = _subject(result.desk, "push-ups")
    assert push.target is not None
    assert push.target.goal <= FOUNDING_PUSH_GOAL
    for call in result.tool_calls:
        if call.name == "update_widget":
            target = call.arguments.get("target")
            if target is not None and int(target) > FOUNDING_PUSH_GOAL:
                assert call.ok is False


async def test_unknown_utterance_does_not_mutate(live_play) -> None:
    result = await live_play("квэкснутый зонд 174")
    assert result.mutated is False


SELECTION_QUOTE = "не роняй таз"
ORPHAN_QUOTE = "беговая экономичность"


async def test_selection_lands_a_clarification_behind_a_question_mark(live_play) -> None:
    """R3: the answer to a selected phrase does not stay in the transcript (#24)."""
    result = await live_play(
        "что это значит?",
        TalkSelection(quote=SELECTION_QUOTE, widget_id="push-ups-counter", step_id="rep-1"),
    )
    assert result.mutated is True
    fresh = [
        row
        for row in result.desk.cues
        if row.subject_id == "push-ups" and row.id not in {"push-ups-brace"}
    ]
    assert fresh, _names(result)
    assert all(row.kind == CueKind.clarification for row in fresh), [row.kind for row in fresh]
    # Never inline at do-time: rep one stays readable (04, P9).
    assert all(row.surface == CueSurface.on_demand for row in fresh), [row.surface for row in fresh]
    assert any(row.quote == SELECTION_QUOTE for row in fresh), [row.quote for row in fresh]
    # The founding correction keeps its place on the tile.
    brace = next(row for row in result.desk.cues if row.id == "push-ups-brace")
    assert brace.surface == CueSurface.do_time
    assert result.text


async def test_selection_with_no_binding_writes_nothing(live_play) -> None:
    """A selection with no bound subject produces no cue — text only (04, 05)."""
    before = founding_desk(now=NOW)
    result = await live_play("что это значит?", TalkSelection(quote=ORPHAN_QUOTE))
    landed = [call for call in result.tool_calls if call.name == "add_cue" and call.ok]
    assert landed == [], [call.arguments for call in landed]
    assert len(result.desk.cues) == len(before.cues)
    assert result.text


# --- R1: the v1 catalog, live ---------------------------------------------
#
# What is asserted here is what the **desk** guarantees: the type lands with a
# payload its runtime can run, its own size, and a real rhythm — `cadence` is a
# hard refusal in the law (`cadence_required`), so a live miss is a bug.
#
# The do-time cue is deliberately *not* asserted here. The prompt asks for one
# and `checklist_shopping` / `timer_meditation` hold that shape as goldens, but
# the desk cannot force a cue the way it forces a rhythm: a cue is a conclusion,
# and an utterance that carries none («список покупок: хлеб, молоко») has
# nothing true to write. Making the model produce one anyway would be inventing
# advice for the person — never-do AI #1 and #2 — which is worse than an empty
# do-time line. Measured on live Haiku: it writes the rhythm reliably and the
# cue only when the turn actually reached a conclusion.


async def test_live_catalog_checklist_lands_with_a_rhythm_and_a_cue(live_play) -> None:
    """A list of lines becomes a practice, not a to-do (never-do #14)."""
    result = await live_play("список покупок на неделю: хлеб, молоко, яблоки")
    assert result.mutated is True
    checklists = [row for row in result.desk.widgets if row.type == WidgetType.checklist]
    assert checklists, _names(result)
    widget = checklists[0]
    assert widget.subject_id not in FOUNDING_IDS
    assert widget.payload.items
    assert len(widget.payload.items) >= 2
    assert all(item.text.strip() for item in widget.payload.items)
    assert widget.tile_size == "4x2"
    # «на неделю» is a rhythm, not a one-off: a practice written with
    # `cadence: none` can never be behind, so drift never reaches it.
    subject = _subject(result.desk, widget.subject_id)
    assert times_per_week(subject.cadence) >= 1
    assert "set_reminder" not in _names(result)


async def test_live_catalog_timer_lands_with_a_length(live_play) -> None:
    result = await live_play("медитация 10 минут каждый день")
    assert result.mutated is True
    timers = [row for row in result.desk.widgets if row.type == WidgetType.timer]
    assert timers, _names(result)
    widget = timers[0]
    # Ten minutes, in seconds — the length is the one thing a timer needs.
    assert widget.payload.seconds == 600
    assert widget.payload.started_at is None
    assert widget.tile_size == "2x2"
    subject = _subject(result.desk, widget.subject_id)
    assert times_per_week(subject.cadence) >= 1


async def test_live_catalog_stepper_only_when_takts_were_asked_for(live_play) -> None:
    result = await live_play("разминка по шагам, два раза в неделю")
    assert result.mutated is True
    steppers = [row for row in result.desk.widgets if row.type == WidgetType.stepper]
    assert steppers, _names(result)
    widget = steppers[0]
    assert widget.payload.beats
    assert len(widget.payload.beats) >= 2
    assert widget.payload.current in (None, 0)
    assert widget.tile_size == "4x2"
    subject = _subject(result.desk, widget.subject_id)
    assert times_per_week(subject.cadence) >= 1


async def test_live_a_plain_practice_does_not_become_a_stepper(live_play) -> None:
    """Q1: takts are for a subject that needs them. «запиши зал» is a counter."""
    result = await live_play("запиши зал")
    assert result.mutated is True
    assert not [row for row in result.desk.widgets if row.type == WidgetType.stepper]


# --- R6: one media on a cue, live -----------------------------------------
#
# The lock measured here is the one thing a model must never do with media: put
# a URL on a movement that nobody wrote ([06] #23 and its trap table — a wrong
# picture on a movement is worse than none). The refusal is in the turn, so
# what the desk shows is the proof: every link on it is one the person sent,
# character for character.
#
# The delivery half — her link actually reaching the cue — is asserted too. It
# is the requirement Q33 came back with: «do not make me leave and search».

HER_LINK = "https://youtu.be/9x1FZrq3kQo"
HER_LINK_UTTERANCE = f"вот видео с этим движением: {HER_LINK} — что значит «негативные повторения»?"
NO_LINK_UTTERANCE = "как понять, что я делаю отжимания правильно?"


def _link_cues(result: TalkTurnResponse) -> list[object]:
    return [row for row in result.desk.cues if row.media is not None and row.media.kind == "link"]


def _invented(result: TalkTurnResponse, words: str) -> list[str]:
    """Every URL the model tried to write that is not in the person's words."""
    urls: list[str] = []
    for call in result.tool_calls:
        media = call.arguments.get("media")
        if not isinstance(media, dict) or media.get("kind") != "link":
            continue
        url = media.get("url")
        if isinstance(url, str) and url not in words:
            urls.append(url)
    return urls


async def test_live_the_link_she_sent_rides_her_cue_unchanged(live_play) -> None:
    result = await live_play(
        HER_LINK_UTTERANCE,
        TalkSelection(quote="негативные повторения", widget_id="push-ups-counter", step_id="rep-1"),
    )
    # Nothing invented: whatever landed came out of her message.
    assert _invented(result, HER_LINK_UTTERANCE) == [], _invented(result, HER_LINK_UTTERANCE)
    for row in result.desk.cues:
        if row.media is not None and row.media.kind == "link":
            assert row.media.url in HER_LINK_UTTERANCE, row.media.url
    # …and her link is on the desk, on a cue that sits behind the «?».
    carried = _link_cues(result)
    assert carried, _names(result)
    assert all(row.media.url == HER_LINK for row in carried), [row.media.url for row in carried]
    assert all(row.surface == CueSurface.on_demand for row in carried), [row.surface for row in carried]
    # At most one per cue is the law's shape: `media` holds a single item.
    assert all(not isinstance(row.media, list) for row in carried)
    # The founding do-time line is untouched — media never became a precondition.
    brace = next(row for row in result.desk.cues if row.id == "push-ups-brace")
    assert brace.surface == CueSurface.do_time
    assert brace.media is None
    assert result.text


async def test_live_no_link_in_the_conversation_means_no_link_on_the_desk(live_play) -> None:
    """She asked about form and sent nothing. A video we sourced for her is the
    trap; an empty `media` is the correct answer, and the step works without one."""
    result = await live_play(NO_LINK_UTTERANCE)
    # Printed, not just asserted: whether the model *reached* for a URL is the
    # measurement this slice owes, and a refused attempt passes silently.
    print(f"[R6 ru no-link] invented={_invented(result, NO_LINK_UTTERANCE)}")
    assert _link_cues(result) == [], [row.media.url for row in _link_cues(result)]
    # If it reached for one anyway, the turn refused it by name and nothing landed.
    for call in result.tool_calls:
        media = call.arguments.get("media")
        if isinstance(media, dict) and media.get("kind") == "link":
            assert call.ok is False
            assert call.error == MEDIA_NOT_IN_CONVERSATION
    assert all(row.media is None for row in result.desk.cues)


# --- Q34 refined: seven checks, one tile, and the request to merge them ----

UPWORK_UTTERANCE = (
    "напоминай мне каждый день в 10 12 15 16:30 18 21 22 что нужно проверить upwork"
    " и галочку на каждую проверку"
)
ONE_WIDGET_UTTERANCE = "а можешь их поместить в один виджет?"
UPWORK_HOURS = [(10, 0), (12, 0), (15, 0), (16, 30), (18, 0), (21, 0), (22, 0)]


def _upwork(desk: Desk):
    return next(
        row
        for row in desk.subjects
        if row.id not in FOUNDING_IDS and row.cadence.period == "day"
    )


async def test_live_seven_hours_land_as_one_practice(live_play) -> None:
    """PO's own line. Seven hours on one window, seven checks in one rhythm."""
    result = await live_play(UPWORK_UTTERANCE)
    assert result.mutated is True
    subject = _upwork(result.desk)
    assert subject.cadence.count == 7
    assert subject.window is not None
    assert [(hour.hour, hour.minute) for hour in subject.window.hours] == UPWORK_HOURS
    # Seven checks, not one case pretending to be seven: a checklist whose
    # lines are the clock times is the shape this decision forbids.
    lists = [row for row in result.desk.widgets if row.type == WidgetType.checklist]
    assert lists == [], [row.title for row in lists]
    assert any(
        row.type in {WidgetType.tick, WidgetType.counter} and row.subject_id == subject.id
        for row in result.desk.widgets
    ), _names(result)


async def test_live_asked_to_merge_them_the_mouth_says_they_already_are(live_play) -> None:
    """The lock: «сказать, не сделав» is a bug — and so is answering a
    different question. Asked to put the seven into one widget, the desk
    already does, and the answer has to say so rather than promise the hours
    again and do nothing."""
    first = await live_play(UPWORK_UTTERANCE)
    result = await live_play(
        ONE_WIDGET_UTTERANCE,
        desk=first.desk,
        thread=[
            ThreadMessage(role="user", text=UPWORK_UTTERANCE),
            ThreadMessage(role="assistant", text=first.text),
        ],
    )
    print(f"[R16 ru one-widget] tools={_names(result)} text={result.text!r}")
    # Nothing to build, so nothing is written — and nothing is undone either.
    assert result.mutated is False
    assert result.tool_calls == []
    assert result.text
    lowered = result.text.casefold()
    # It already is one tile, and the answer has to say so.
    assert "уже" in lowered, result.text
    # Not the old failure: a promise about the hours instead of an answer.
    assert "напомню в эти семь" not in lowered
