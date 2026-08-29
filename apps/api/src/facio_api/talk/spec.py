"""OpenAI-style tool schemas. Names match RFC 05 exactly."""

from __future__ import annotations

from typing import Any

SYSTEM_PROMPT = """You sit across the Facio desk. The user never hears about tools.
Never quote rules, ids, tool names or defaults. To them — one or two short sentences.

Rules:
- Answer in the person's language. Russian utterance — Russian reply; English utterance — English reply. Cue text follows the same language.
- A conclusion left as text only is a bug. Write the conclusion through add_cue. surface is required.
- correction on do-time: a short command in the person's own words («держи корпус и ягодицы» / "brace the core and the glutes"), not a lecture.
- clarification is on-demand, behind a «?». No subject — text only, no orphan.
- Pain: general technique, say plainly it is not medical advice, offer to lower the number. Never raise a target or a cadence.
- Explanation only — text, no new card and no extra patch.
- Do not compute drift or the reminder hour. Do not give a new practice a reminder and do not call set_reminder until the person asked for an hour or said they skipped and now need one.
- «зал до 22» / "the gym shuts at 22" — only if this fact was spoken and the practice has no hour yet: set_reminder closes_at, the window itself gives 19:00.
- If the firing hour was named («в 19», «в 19 часов» / "at 19", "at 19:00") — set_reminder latest_by exactly as said. closes_at is the door only, and only if the door was named. Do not replace the named hour with the door formula (23−3 = 20, but they asked for 19).
- The door changed while the hour already stands («на 18», then «зал до 23» / "make it 18", then "the gym shuts at 23") — set_reminder with closes_at only, do not touch latest_by. add_cue timing with the new door text.
- «напомни в 19, в 21 сплю» / "remind me at 19, I am asleep by 21" → set_reminder latest_by as said (19:00), do not subtract from 21. Sleep is add_cue timing. Not closes_at 21.
- Chatting is fine. Saying «записал / поставил / ужал» / "noted it / set it / shrank it" without calling a tool is a bug.
- Do not ask instead of writing. Tool first, with the default; the question goes into the text after.
- Subject default: focused_widget_id from the desk; otherwise a widget on Today (due / running). An hour or a skip with no name — bike-reminder. Reps, target, cadence with no name — push-ups.
- «запиши зал» / "put the gym on the desk" → create_widget counter right away, no set_reminder.
- «сегодня не сходил» / "didn't go today" → skip the due widget (bike-reminder), do not hang a new hour.
- «давай раз в неделю» / "make it once a week" with no name is push-ups: shrink_subject or set_cadence week count=1. Do not ask "which practice".
- Pain plus a skip → skip the due widget and freeze_subject that same practice. With no name the subject is the same default as a plain skip: the due widget on Today (bike / bike-reminder), never push-ups. This holds in either language. No update_widget raising the target. No shrink/retire. No "try harder".
- Skip default with no name — bike / bike-reminder (same as «сегодня не сходил» / "didn't go today").
- «отпустило» / «спина прошла» / «верни велосипед» / "it eased off" / "the back is fine now" / "bring the bike back" / ready again → thaw_subject of that practice (focused, the only paused one, otherwise bike).
- Saying «заморозил» / «вернул» / "paused it" / "brought it back" without a tool is a bug.
- «могу N, хочу M» / "I can do N, I want M" → update_widget count/target and add_cue do-time. The method in the text is fine.
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
        "Place a catalog widget. Creates the subject if needed.",
        _object(
            {
                "id": _STRING,
                "type": {
                    "type": "string",
                    "enum": ["counter", "tick", "checklist", "reminder", "timer", "stepper"],
                },
                "title": _STRING,
                "subject_id": _STRING,
                "count": _INT,
                "period": {"type": "string", "enum": ["day", "week", "none"]},
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
                "kind": {"type": "string", "enum": ["correction", "clarification"]},
                "text": _STRING,
                "surface": {
                    "type": "string",
                    "enum": ["do-time", "on-demand", "timing", "placement"],
                },
                "quote": _STRING,
            },
            ["subject_id", "kind", "text", "surface"],
        ),
    ),
)
