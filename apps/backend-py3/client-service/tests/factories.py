"""Sample LLM payloads matching docs/mvp Path + instant_answer contracts."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


def sample_path_state(**overrides: Any) -> dict[str, Any]:
    state: dict[str, Any] = {
        "title": "Карбонара на двоих",
        "summary": (
            "За вечер купим продукты и приготовим карбонару на двоих. "
            "Сначала покупки со списком, потом готовка по шагам."
        ),
        "outcome": "Приготовить карбонару на двоих",
        "paraphrase": "Ок — ведём к карбонаре на двоих сегодня вечером",
        "success_criteria": "Два порции карбонары на столе",
        "horizon": "1 evening, ~45 min",
        "domain": "cooking",
        "tags": ["pasta", "dinner", "carbonara"],
        "groups": [
            {
                "id": "shop",
                "title": "Покупки",
                "description": "Собрать ингредиенты до готовки.",
                "sort": 0,
            },
            {
                "id": "cook",
                "title": "Готовка",
                "description": "Собрать блюдо по классическому методу.",
                "sort": 1,
            },
        ],
        "actions": [
            {
                "id": "buy",
                "title": "Купить продукты",
                "why": "Без ингредиентов блюдо не собрать",
                "detail": None,
                "estimate_min": 20,
                "day_offset": 0,
                "sort": 0,
                "group_id": "shop",
                "checklist_items": [
                    {"id": "eggs", "title": "Яйца", "done": False, "sort": 0},
                    {
                        "id": "guanciale",
                        "title": "Гуанчиале",
                        "done": False,
                        "sort": 1,
                    },
                    {
                        "id": "pecorino",
                        "title": "Пекорино",
                        "done": False,
                        "sort": 2,
                    },
                ],
            },
            {
                "id": "cook",
                "title": "Сварить пасту и соус",
                "why": "Это основной шаг к готовому блюду",
                "detail": "Аль денте, соус на желтках и сыре",
                "estimate_min": 25,
                "day_offset": 0,
                "sort": 1,
                "group_id": "cook",
                "checklist_items": [],
            },
        ],
        "questions": [
            {
                "id": "q_servings",
                "prompt": "На сколько порций?",
                "options": ["1", "2", "4"],
            },
            {
                "id": "q_guanciale",
                "prompt": "Гуанчиале или бекон?",
                "options": ["гуанчиале", "бекон"],
            },
        ],
        "resources": [],
        "milestones": ["продукты куплены", "блюдо готово"],
    }
    state.update(overrides)
    return state


def sample_create_path(**overrides: Any) -> dict[str, Any]:
    path = sample_path_state(**overrides.pop("path_overrides", {}))
    payload = {"kind": "path", "path": path, "instant_answer": None}
    payload.update(overrides)
    return payload


def sample_instant_answer(**overrides: Any) -> dict[str, Any]:
    payload = {
        "kind": "instant_answer",
        "path": None,
        "instant_answer": {
            "label": "Это скорее вопрос, не цель",
            "answer": "2^100 = 1267650600228229401496703205376",
            "goal_suggestions": [
                "Выучить степени двойки наизусть",
                "Разобрать битовую арифметику",
            ],
            "domain": "learning",
        },
    }
    if "instant_answer" in overrides:
        payload["instant_answer"].update(overrides.pop("instant_answer"))
    payload.update(overrides)
    return payload


def refined_path_state(base: dict[str, Any] | None = None) -> dict[str, Any]:
    state = deepcopy(base or sample_path_state())
    state["title"] = "Карбонара на 2 с гуанчиале"
    state["summary"] = (
        "Путь уточнён под 2 порции и гуанчиале. "
        "Покупки с количествами, затем классическая готовка."
    )
    state["paraphrase"] = "Ок — карбонара на 2 порции с гуанчиале"
    state["questions"] = []
    state["actions"][0]["checklist_items"] = [
        {"id": "eggs", "title": "Яйца ×4", "done": False, "sort": 0},
        {
            "id": "guanciale",
            "title": "Гуанчиале 150г",
            "done": False,
            "sort": 1,
        },
        {"id": "pecorino", "title": "Пекорино 80г", "done": False, "sort": 2},
    ]
    return state
