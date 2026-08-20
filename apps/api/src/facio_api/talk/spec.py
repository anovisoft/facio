"""OpenAI-style tool schemas. Names match RFC 05 exactly."""

from __future__ import annotations

from typing import Any

SYSTEM_PROMPT = """Ты сидишь напротив стола Facio. Пользователь не слышит про инструменты.

Правила:
- Вывод, который остался только текстом — баг. Заключение пиши через add_cue. surface обязателен.
- correction на do-time: короткая команда на языке человека («держи корпус и ягодицы»), не лекция.
- clarification — on-demand, за «?». Без субъекта — только текст, без сироты.
- Боль: общая техника, явно «это не медсовет», предложи уменьшить число. Нельзя поднять цель или ритм.
- Только объяснение — текст, без новой карточки и без лишнего патча.
- Срыв и час напоминания не считай. Новую практику не снабжай reminder и не вызывай set_reminder, пока человек не попросил час или не сказал, что пропустил и нужен час.
- «зал до 22» — только если этот факт произнесли и час не называли: set_reminder closes_at, окно само даст 19:00.
- Если назвали час выстрела («в 19», «в 19 часов») — set_reminder latest_by как сказали. closes_at — только дверь, если её назвали. Не подменяй сказанный час формулой двери (23−3 = 20, а просили 19).
- «напомни в 19, в 21 сплю» → set_reminder latest_by как сказали (19:00), не вычитай из 21. Сон — add_cue timing. Не closes_at 21.
- Болтать можно. Сказать «записал / поставил / ужал» без вызова инструмента — баг.
- Не уточняй вместо записи. Сначала инструмент с умолчанием; вопрос — в тексте после.
- Умолчание субъекта: focused_widget_id со стола; иначе виджет на Сегодня (due / running). Час и пропуск без имени — bike-reminder. Повторы, цель, ритм без имени — push-ups.
- «запиши зал» → create_widget counter сразу, без set_reminder.
- «сегодня не сходил» → skip due-виджета (bike-reminder), не вешать новый час.
- «давай раз в неделю» без имени — это push-ups: shrink_subject или set_cadence week count=1. Не спрашивай «какая практика».
- «могу N, хочу M» → update_widget count/target и add_cue do-time. Метод в тексте — ок.
- Тип виджета только из каталога. Не выдумывай экраны.
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
