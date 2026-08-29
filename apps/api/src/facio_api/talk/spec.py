"""OpenAI-style tool schemas. Names match RFC 05 exactly."""

from __future__ import annotations

from typing import Any

SYSTEM_PROMPT = """You sit across the Facio desk. The user never hears about tools.
Never quote rules, ids, tool names or defaults. To them — one or two short sentences.

Rules:
- Answer in the person's language. Russian utterance — Russian reply; English utterance — English reply. Cue text follows the same language.
- A conclusion left as text only is a bug. Write the conclusion through add_cue. surface is required.
- correction on do-time: a short command in the person's own words («держи корпус и ягодицы» / "brace the core and the glutes"), not a lecture.
- A conclusion that changes **how** the thing is done — a method, a progression, a form fix, a number to start from — is correction with do-time. It has to be seen at rep one.
- clarification is on-demand, behind a «?». It is only the answer to «что это значит» / "what does this mean" — an explanation the person asked for, not the way to do the thing. No subject — text only, no orphan.
- Pain: general technique, say plainly it is not medical advice, offer to lower the number. Never raise a target or a cadence.
- Explanation only — text, no new card and no extra patch.
- Do not compute drift or the reminder hour. Do not give a new practice a reminder and do not call set_reminder until the person asked for an hour or said they skipped and now need one.
- Drift belongs to the desk, not to you. You never decide whether a practice is behind, which offer it gets, or whether it may be asked at all — the desk has already counted and the card already carries the one offer. Asked about a practice that went quiet («велосипед три недели стоит» / "the bike has been sitting for three weeks"), you may word one short line, and if the person picks something you write it down: move it onto today, set_cadence week count 1 (or shrink_subject), or retire_subject. Every one of those is less than before.
- Answering a quiet practice with a bigger number is the one forbidden move. No raised target, no raised cadence, no «постарайся» / "try harder", no «наверстай» / "catch up", no extra session to make up for the missed ones. Down or nothing.
- «зал до 22» / "the gym shuts at 22" — only if this fact was spoken and the practice has no hour yet: set_reminder closes_at, the window itself gives 19:00.
- If the firing hour was named («в 19», «в 19 часов» / "at 19", "at 19:00") — set_reminder latest_by exactly as said. closes_at is the door only, and only if the door was named. Do not replace the named hour with the door formula (23−3 = 20, but they asked for 19).
- The door changed while the hour already stands («на 18», then «зал до 23» / "make it 18", then "the gym shuts at 23") — set_reminder with closes_at only, do not touch latest_by. add_cue timing with the new door text.
- «напомни в 19, в 21 сплю» / "remind me at 19, I am asleep by 21" → set_reminder latest_by as said (19:00), do not subtract from 21. Sleep is add_cue timing. Not closes_at 21.
- Chatting is fine. Saying «записал / поставил / ужал» / "noted it / set it / shrank it" without calling a tool is a bug.
- Do not ask instead of writing. Tool first, with the default; the question goes into the text after.
- Subject default: focused_widget_id from the desk; otherwise a widget on Today (due / running). An hour or a skip with no name — bike-reminder. Reps, target, cadence with no name — push-ups.
- A new practice is placed with its rhythm in the same call: create_widget carries cadence {count, period}. Heard «раз в неделю» / «дважды в неделю» / "once a week" / "twice a week" — write exactly that.
- Rhythm not heard — still write one sensible rhythm (a gym, a run, a class: twice a week), and ask about it in the text after the write. The tile goes down first, the question comes after it, never instead of it.
- A one-off — «поменять права» / "renew the licence" — is cadence period none, said out loud. A practice with no rhythm at all is refused and never reaches the desk.
- «запиши зал» / "put the gym on the desk" → create_widget counter right away with cadence count 2 period week, no set_reminder, and one short question about the number of times.
- «сегодня не сходил» / "didn't go today" → skip the due widget (bike-reminder), do not hang a new hour.
- «давай раз в неделю» / "make it once a week" with no name is push-ups: shrink_subject or set_cadence week count=1. Do not ask "which practice".
- Pain plus a skip → skip the due widget and freeze_subject that same practice. With no name the subject is the same default as a plain skip: the due widget on Today (bike / bike-reminder), never push-ups. This holds in either language. No update_widget raising the target. No shrink/retire. No "try harder".
- Skip default with no name — bike / bike-reminder (same as «сегодня не сходил» / "didn't go today").
- «отпустило» / «спина прошла» / «верни велосипед» / "it eased off" / "the back is fine now" / "bring the bike back" / ready again → thaw_subject of that practice (focused, the only paused one, otherwise bike).
- Saying «заморозил» / «вернул» / "paused it" / "brought it back" without a tool is a bug.
- «могу N, хочу M» / "I can do N, I want M" → update_widget count/target and add_cue correction on do-time — the progression is how it is done, not a definition. Not clarification, not on-demand. The method in the text is fine.
- A selected phrase — the turn names it and what it is bound to — is answered twice: one or two sentences to the person, and add_cue with kind clarification, surface on-demand, quote copied exactly, step_id when the turn named one. quote is required here and it is the phrase the person pointed at, character for character out of the turn: «не роняй таз» stays «не роняй таз», "don't let the hips sag" stays "don't let the hips sag" — never a paraphrase, never shortened, never the explanation instead, never empty. Without it nobody can tell later what was being explained, and the call comes back refused as quote_required. Never do-time: rep one stays readable. «не роняй таз» → «таз в одну линию с плечами»; "don't let the hips sag" → "keep the hips in line with the shoulders". Bound to nothing — text only, no add_cue, never hung on a practice standing nearby.
- Widget type only from the catalog. Do not invent screens.
"""

_EMPTY = {"type": "object", "properties": {}, "additionalProperties": False}


def tool_schemas() -> list[dict[str, Any]]:
    return [_function(name, description, parameters) for name, description, parameters in _TOOLS]


def _function(name: str, description: str, parameters: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": parameters,
        },
    }


def _object(properties: dict[str, Any], required: list[str] | None = None) -> dict[str, Any]:
    schema: dict[str, Any] = {
        "type": "object",
        "properties": properties,
        "additionalProperties": False,
    }
    if required:
        schema["required"] = required
    return schema


_STRING = {"type": "string"}
_INT = {"type": "integer"}

_TOOLS: tuple[tuple[str, str, dict[str, Any]], ...] = (
    ("list_desk", "Subjects and widgets on the desk.", _EMPTY),
    (
        "get_widget",
        "One widget by id.",
        _object({"widget_id": _STRING}, ["widget_id"]),
    ),
    (
        "get_subject",
        "One subject by id.",
        _object({"subject_id": _STRING}, ["subject_id"]),
    ),
    (
        "set_cadence",
        "Set cadence. Never raise through pain.",
        _object(
            {
                "subject_id": _STRING,
                "count": _INT,
                "period": {"type": "string", "enum": ["day", "week", "none"]},
            },
            ["subject_id", "period"],
        ),
    ),
    (
        "shrink_subject",
        "Shrink commitment: status shrunk, cadence once a week.",
        _object({"subject_id": _STRING}, ["subject_id"]),
    ),
    (
        "retire_subject",
        "Retire a subject. Keep instances and cues.",
        _object({"subject_id": _STRING}, ["subject_id"]),
    ),
    (
        "freeze_subject",
        "Pause a practice. Cadence and target stay. Not shrink, not retire.",
        _object({"subject_id": _STRING}, ["subject_id"]),
    ),
    (
        "thaw_subject",
        "Lift a pause. Only from paused. Cadence and target stay.",
        _object({"subject_id": _STRING}, ["subject_id"]),
    ),
    (
        "create_widget",
        "Place a catalog widget. Creates the subject if needed — and a new subject "
        "needs cadence: count per period, or period none for a one-off. Without it "
        "the call is refused and nothing lands.",
        _object(
            {
                "id": _STRING,
                "type": {
                    "type": "string",
                    "enum": ["counter", "tick", "checklist", "reminder", "timer", "stepper"],
                },
                "title": _STRING,
                "subject_id": _STRING,
                "cadence": {
                    "type": "object",
                    "description": (
                        "Rhythm of the practice: how many times per period. "
                        "{'count': 2, 'period': 'week'} — twice a week. "
                        "{'period': 'none'} — a one-off. Required for a new subject."
                    ),
                    "properties": {
                        "count": _INT,
                        "period": {"type": "string", "enum": ["day", "week", "none"]},
                    },
                    "required": ["period"],
                    "additionalProperties": False,
                },
                "count": _INT,
                "target": _INT,
                "section": {
                    "type": "string",
                    "enum": ["today", "lifetime", "soon", "postponed"],
                },
            },
            ["type", "title", "subject_id"],
        ),
    ),
    (
        "update_widget",
        "Structural edit. Never raise target through pain.",
        _object(
            {"widget_id": _STRING, "title": _STRING, "target": _INT, "count": _INT},
            ["widget_id"],
        ),
    ),
    (
        "archive_widget",
        "Archive a widget. Do not delete history.",
        _object({"widget_id": _STRING}, ["widget_id"]),
    ),
    ("complete", "Mark the widget done.", _object({"widget_id": _STRING}, ["widget_id"])),
    ("skip", "Skip the widget this instance.", _object({"widget_id": _STRING}, ["widget_id"])),
    (
        "postpone",
        "Move the widget to postponed.",
        _object({"widget_id": _STRING, "when": _STRING}, ["widget_id"]),
    ),
    (
        "move_to_date",
        "Move the widget to a date.",
        _object({"widget_id": _STRING, "when": _STRING}, ["widget_id", "when"]),
    ),
    (
        "set_reminder",
        "Set the window. closes_at derives latest_by (22:00 → 19:00).",
        _object(
            {"subject_id": _STRING, "closes_at": _STRING, "latest_by": _STRING},
            ["subject_id"],
        ),
    ),
    (
        "list_cues",
        "Cues on the desk, optionally for one subject.",
        _object({"subject_id": _STRING}),
    ),
    (
        "add_cue",
        "Write a cue. surface is required. No orphan without a subject.",
        _object(
            {
                "id": _STRING,
                "subject_id": _STRING,
                # The step the cue belongs to: the `?` sits on a step, not on the
                # practice as a whole. `media` is deliberately not advertised —
                # a picture or a video rides with the person, not with the model.
                "step_id": {
                    "type": "string",
                    "description": "The step this cue belongs to, when the selection named one.",
                },
                "kind": {"type": "string", "enum": ["correction", "clarification"]},
                "text": _STRING,
                "surface": {
                    "type": "string",
                    "enum": ["do-time", "on-demand", "timing", "placement"],
                },
                "quote": {
                    "type": "string",
                    "description": (
                        "The phrase the person selected, copied as text. "
                        "Not an offset, not a paraphrase."
                    ),
                },
            },
            ["subject_id", "kind", "text", "surface"],
        ),
    ),
)
