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
        "cycle": {
            "index": 1,
            "horizon_days": 1,
            "status": "draft",
            "goal_for_cycle": "Карбонара на двоих сегодня",
        },
        "days": [
            {
                "day_index": 0,
                "kind": "cook_session",
                "title": "Вечер готовки",
                "summary": "Покупки и карбонара за один заход.",
            }
        ],
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
                "plugin_hints": [],
                "timers": [],
                "counter": None,
                "timeline": None,
                "interval_plan": None,
                "stepper": None,
            },
            {
                "id": "sear",
                "title": "Обжарить гуанчиале",
                "why": "Параллельная подготовка мяса",
                "detail": "До золотистой корочки",
                "estimate_min": 8,
                "day_offset": 0,
                "sort": 1,
                "group_id": "cook",
                "checklist_items": [],
                "plugin_hints": ["timers"],
                "timers": [],
                "counter": None,
                "timeline": None,
                "interval_plan": None,
                "stepper": None,
            },
            {
                "id": "cook",
                "title": "Сварить пасту и соус",
                "why": "Это основной шаг к готовому блюду",
                "detail": "Аль денте, соус на желтках и сыре",
                "estimate_min": 25,
                "day_offset": 0,
                "sort": 2,
                "group_id": "cook",
                "checklist_items": [],
                "plugin_hints": ["timeline"],
                "timers": [],
                "counter": None,
                "timeline": None,
                "interval_plan": None,
                "stepper": None,
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


def sample_plugins_materialize(**overrides: Any) -> dict[str, Any]:
    """Create #3 payload for carbonara cook (timeline) + sear (timers only)."""
    payload: dict[str, Any] = {
        "actions": [
            {
                "action_id": "sear",
                "timers": [
                    {
                        "id": "guanciale",
                        "title": "Обжарить гуанчиале",
                        "duration_sec": 480,
                        "signal": "nudge",
                        "parallel_group": None,
                    },
                ],
                "counter": None,
                "timeline": None,
                "interval_plan": None,
                "stepper": None,
            },
            {
                "action_id": "cook",
                "timers": [],
                "counter": None,
                "timeline": {
                    "duration_sec": 480,
                    "markers": [
                        {"sec": 0, "title": "Паста в воду", "signal": "nudge"},
                        {"sec": 120, "title": "Помешать", "signal": "nudge"},
                        {"sec": 300, "title": "Помешать ещё", "signal": "nudge"},
                        {
                            "sec": 480,
                            "title": "Лапша al dente",
                            "signal": "alert",
                        },
                    ],
                },
                "interval_plan": None,
                "stepper": None,
            },
        ]
    }
    payload.update(overrides)
    return payload


def _sample_train_stepper(*, measure_target: int = 15) -> dict[str, Any]:
    return {
        "beats": [
            {
                "id": "m0",
                "kind": "measure",
                "title": "Замер",
                "counter": {
                    "label": "повторы",
                    "target": measure_target,
                    "current": 0,
                    "step": 1,
                },
                "duration_sec": None,
                "signal": "nudge",
            },
            {
                "id": "r0",
                "kind": "rest",
                "title": "Отдых",
                "counter": None,
                "duration_sec": 180,
                "signal": "nudge",
            },
            {
                "id": "w1",
                "kind": "work",
                "title": "Подход 1",
                "counter": {
                    "label": "повторы",
                    "target": 12,
                    "current": 0,
                    "step": 1,
                },
                "duration_sec": None,
                "signal": "nudge",
            },
            {
                "id": "r1",
                "kind": "rest",
                "title": "Отдых",
                "counter": None,
                "duration_sec": 90,
                "signal": "nudge",
            },
            {
                "id": "w2",
                "kind": "work",
                "title": "Подход 2",
                "counter": {
                    "label": "повторы",
                    "target": 12,
                    "current": 0,
                    "step": 1,
                },
                "duration_sec": None,
                "signal": "alert",
            },
        ]
    }


def sample_fitness_plugins_materialize(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "actions": [
            {
                "action_id": "d0",
                "timers": [],
                "counter": None,
                "timeline": None,
                "interval_plan": None,
                "stepper": _sample_train_stepper(measure_target=15),
            },
            {
                "action_id": "d2",
                "timers": [],
                "counter": None,
                "timeline": None,
                "interval_plan": None,
                "stepper": _sample_train_stepper(measure_target=12),
            },
            {
                "action_id": "d4",
                "timers": [],
                "counter": None,
                "timeline": None,
                "interval_plan": None,
                "stepper": _sample_train_stepper(measure_target=12),
            },
            {
                "action_id": "d6",
                "timers": [],
                "counter": None,
                "timeline": None,
                "interval_plan": None,
                "stepper": _sample_train_stepper(measure_target=12),
            },
        ]
    }
    payload.update(overrides)
    return payload


def sample_fitness_path_state(**overrides: Any) -> dict[str, Any]:
    """Push-ups week: 7-day cycle with train/rest mix + stepper hints."""
    days = []
    actions = []
    kinds = [
        ("train", "Силовая A", "Короткие подходы."),
        ("rest", "Отдых + мобилити", "Восстановление без силовых."),
        ("train", "Силовая B", "Повторяем объём."),
        ("rest", "Отдых", "Лёгкая мобилити."),
        ("train", "Силовая C", "Третья силовая."),
        ("rest", "Отдых", "Спокойный день."),
        ("train", "Силовая D", "Закрываем неделю."),
    ]
    for i, (kind, title, summary) in enumerate(kinds):
        days.append(
            {
                "day_index": i,
                "kind": kind,
                "title": title,
                "summary": summary,
            }
        )
        if kind == "train":
            action: dict[str, Any] = {
                "id": f"d{i}",
                "title": "Силовая сессия",
                "why": f"Силовой день {i // 2 + 1} двигает к 30 отжиманиям",
                "detail": "Замер → отдых → подходы с отдыхом между.",
                "estimate_min": 20,
                "day_offset": i,
                "sort": i,
                "group_id": None,
                "checklist_items": [],
                "plugin_hints": ["stepper"],
                "timers": [],
                "counter": None,
                "timeline": None,
                "interval_plan": None,
                "stepper": None,
            }
            actions.append(action)
        else:
            actions.append(
                {
                    "id": f"d{i}",
                    "title": "Лёгкая мобилити",
                    "why": "Отдых — часть программы, не пропуск",
                    "detail": "5–10 минут мягкой подвижности.",
                    "estimate_min": 10,
                    "day_offset": i,
                    "sort": i,
                    "group_id": None,
                    "checklist_items": [],
                    "plugin_hints": [],
                    "timers": [],
                    "counter": None,
                    "timeline": None,
                    "interval_plan": None,
                    "stepper": None,
                }
            )
    state: dict[str, Any] = {
        "title": "К 30 отжиманиям — неделя 1",
        "summary": (
            "За ~6–8 недель дойдём к 30. Эта неделя — база: "
            "силовые чередуются с отдыхом."
        ),
        "outcome": "Заложить базу к 30 отжиманиям",
        "paraphrase": "Ок — ведём к: 30 отжиманий, неделя базы",
        "success_criteria": "Закрыты силовые дни недели",
        "horizon": "7 дней, ~15 мин в силовые",
        "domain": "fitness",
        "tags": ["push-ups"],
        "cycle": {
            "index": 1,
            "horizon_days": 7,
            "status": "draft",
            "goal_for_cycle": "Неделя базы",
        },
        "days": days,
        "groups": [],
        "actions": actions,
        "questions": [
            {
                "id": "level",
                "prompt": "Сколько отжиманий сейчас?",
                "options": ["0–5", "6–15", "16+"],
            },
            {
                "id": "days",
                "prompt": "Дней в неделю?",
                "options": ["3", "4", "5+"],
            },
        ],
        "resources": [],
        "milestones": [],
    }
    state.update(overrides)
    return state


def sample_fitness_overshoot_path_state(**overrides: Any) -> dict[str, Any]:
    """Reproduces the fit_sample hotfix bug: gate framed a 4–6 week program,
    the model emitted horizon_days=35 with actions only through day_offset
    19 and a 15-day hollow rest tail (days 20–34, zero actions attached).
    """
    days: list[dict[str, Any]] = []
    actions: list[dict[str, Any]] = []
    for i in range(20):
        kind = "train" if i % 2 == 0 else "rest"
        days.append(
            {
                "day_index": i,
                "kind": kind,
                "title": "Силовая" if kind == "train" else "Отдых",
                "summary": None,
            }
        )
        if kind == "train" or i == 19:
            actions.append(
                {
                    "id": f"d{i}",
                    "title": "Подходы отжиманий",
                    "why": "Силовой день двигает к 30 отжиманиям",
                    "detail": "3 коротких подхода.",
                    "estimate_min": 15,
                    "day_offset": i,
                    "sort": i,
                    "group_id": None,
                    "checklist_items": [],
                    "plugin_hints": ["stepper"],
                    "timers": [],
                    "counter": None,
                    "timeline": None,
                    "interval_plan": None,
                    "stepper": None,
                }
            )
    for i in range(20, 35):
        days.append(
            {
                "day_index": i,
                "kind": "rest",
                "title": "Отдых",
                "summary": None,
            }
        )
    state: dict[str, Any] = {
        "title": "К 30 отжиманиям",
        "summary": "За ~6–8 недель дойдём к 30 отжиманиям. Эта неделя — база.",
        "outcome": "Заложить базу к 30 отжиманиям",
        "paraphrase": "Ок — ведём к: 30 отжиманий",
        "success_criteria": "Закрыты силовые дни",
        "horizon": "4–6 недель, ~15 мин в силовые",
        "domain": "fitness",
        "tags": ["push-ups"],
        "cycle": {
            "index": 1,
            "horizon_days": 35,
            "status": "draft",
            "goal_for_cycle": "",
        },
        "days": days,
        "groups": [],
        "actions": actions,
        "questions": [],
        "resources": [],
        "milestones": [],
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
