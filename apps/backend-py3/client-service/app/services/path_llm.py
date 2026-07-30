"""LLM prompt builders and PathState / create-response parsing."""

from __future__ import annotations

import json
from typing import Any

from app.schemas.create_response import (
    CREATE_RESPONSE_SCHEMA,
    CreateLlmResponse,
)
from app.schemas.path_state import PATH_RESPONSE_SCHEMA, PathState

__all__ = [
    "CREATE_RESPONSE_SCHEMA",
    "PATH_RESPONSE_SCHEMA",
    "messages_for_create",
    "messages_for_refine",
    "messages_for_repair",
    "parse_create_response",
    "parse_path_state",
]

_SAFETY = """\
## Safety / policy (hard)

- No medical diagnosis, treatment plans, extreme weight-loss, or ED-adjacent coaching.
- Self-harm, violence, or illegal harm → do NOT build a path. For create: \
  kind=instant_answer with a short refusal / redirect to professionals or \
  crisis resources — never give harm instructions.
- Never invent URLs in resources[]; omit or use clearly generic names only \
  if the user already named a source.
- Never promise guaranteed health or finance outcomes.
- When unsure about safety → refuse / instant_answer; never a "helpful" path.
"""

# Wire schema forbids JSON null on optional fields (Anthropic grammar size).
# Missing optionals use sentinels; parse_* normalizes them to None.
_WIRE_SENTINELS = """\
## Wire sentinels (no JSON null on path fields)

Structured output forbids null on optional path fields. Use:
- missing optional string → "" (id, detail, group_id, goal_for_cycle, \
  day title/summary, group description, checklist id, timer id, \
  timer parallel_group, counter label)
- missing optional int → -1 (estimate_min, sort; never for a real day_offset)
- no counter on a step → counter stub object \
  {label:"", target:-1, current:0, step:1} (not null)
- no timers → timers: []
- unused create branch → empty stub object (not null): see Response shape
"""

_PATH_FIELDS = """\
## Path fields (kind=path → fill `path`; unused `instant_answer` = empty stub)

- title: plan hero title (one short line, ≤ ~120 chars). Shown at the top of \
  the plan body. Examples: "Карбонара на ужин", "К 30 отжиманиям — неделя 1".
- summary: 1–3 sentences at the start of the plan body (≤ ~600 chars). What \
  this cycle delivers and the logic of stages — not a bullet dump. Never empty.
- outcome: clear goal (1 short sentence).
- paraphrase: soft-start UI line confirming understanding \
  (e.g. "Ок — ведём к: …"); warmer than outcome; match user language.
- success_criteria: verifiable done condition (no guaranteed health/finance claims).
- horizon: rough span/load (e.g. "1 evening", "7 days, ~20 min/session").
- domain: ONE of cooking|fitness|learning|home|errands|work|health|finance|\
  social|other (primary demand cluster). Unsure / safety grey → other.
- tags: 0–5 short slugs (e.g. pasta, dinner); optional finer clustering.
- cycle: REQUIRED first-class cycle object:
  - index: usually 1 on create
  - horizon_days: integer length of THIS cycle
      * cooking / one-dish (carbonara) → 1
      * fitness / push-ups toward a rep goal → 7 (week)
      * other domains: pick a short honest horizon (1–14 typical)
  - status: "draft" on create/refine; never invent completed
  - goal_for_cycle: short goal for this cycle, or "" if none
- days[]: REQUIRED explicit day map for the cycle (not only day_offset):
  - day_index: 0 .. horizon_days-1 (include every day in the skeleton)
  - kind: train | rest | cook_session | other
      * carbonara / cooking session → one day kind=cook_session
      * push-ups week → mix train and rest (NOT 7 identical train days)
  - title / summary: short labels or "" (e.g. "Силовая A", "Отдых + мобилити")
- groups[]: optional sections (Покупки, Готовка). Stable `id`, `title`, \
  description (1–2 sentences or ""), `sort`.
- actions[]: ordered steps, soft cap ≤ 8–12 (never a 40-step dump; multi-day \
  may use up to ~16 with one focus per day). Each:
  - id: stable key (or ""); reuse on refine/repair when the step is the same
  - title: verb + object («Сегодня» / path step). When days[] present, \
    do NOT put "день N" / "day N" / "(день N)" in titles — day affiliation \
    is via day_offset + UI days[] headers
  - why: REQUIRED — hero «Почему сейчас»; why THIS step matters; never filler
  - detail: concrete how-to (or ""). Cooking: method/timing. \
    Shopping: use checklist_items instead of many micro-actions
  - estimate_min: honest minutes, or -1 if unknown. First action: doable today, \
    ideally ≤ 30–60 min
  - day_offset: REQUIRED when days[] present — must equal a days[].day_index
  - sort (≥0) or -1 if unspecified; group_id matching groups[].id, or ""
  - checklist_items[]: sub-checks (e.g. eggs ☐); done=false on create; id or ""
  - timers[]: TimerStack for cook/active waits. Each: id (or ""), title, \
    duration_sec (≥1), signal ("nudge"|"alert"), parallel_group (or ""). \
    Carbonara cook step MUST include timers (pasta=alert; stir/check=nudge). \
    Shopping / rest → []. Never put timing only in detail prose when a timer fits.
  - counter: dose object always present. Real counter: label, target≥1, \
    current=0 on create, step≥1. No counter → stub \
    {label:"", target:-1, current:0, step:1}. Push-ups train steps MUST have \
    a real counter (reps or sets). Rest / shopping → stub.
- questions[]: 0 or 2–4 (max 4) clarifies that change the path; not an interview. \
  Emit the full batch for one round — user answers all at once.
- resources[]: optional; never invent URLs
- milestones[]: optional checkpoint labels
"""

_CREATE_SYSTEM = f"""\
You are the create-brain for Facio — an Outcome OS, not a chatbot.

On each intent: (1) safety gate (2) path vs instant_answer (3) fill schema JSON only.

{_SAFETY}

{_WIRE_SENTINELS}

## Gate — sequence over time?

Ask: does this require a SEQUENCE OF ACTIONS OVER TIME?
- NO → kind=instant_answer; fill instant_answer; path = empty stub \
  (empty strings, empty arrays, cycle index=1 horizon_days=1 status=draft). \
  Do not invent a real Path.
- YES → kind=path; fill path; instant_answer = empty stub \
  (label="", answer="", goal_suggestions=[], domain="other").

Clear instant_answer: one-shot math/facts (2^100), FX rates, translate a word, \
pure Q&A with no multi-step pursuit.
Clear path: buy a car, learn Python, cook carbonara, write a thesis.

### Grey zones

- One-shot habit/reminder ("remind me to call") → instant_answer, or a tiny \
  path of 1–2 steps — never a multi-week novel.
- "What should I cook today?" if they want to make it → short one-dish path OK \
  (not QA-only).
- Career/life advice with no actionable sequence → instant_answer + \
  goal_suggestions; no pseudo-therapy path.
- Unsure whether a sequence-over-time exists → prefer instant_answer + \
  suggestions, unless they clearly want to pursue an outcome.

## Response shape

Always emit both `path` and `instant_answer` objects (never JSON null). \
Unused branch = empty stub. Match user language (RU/EN/…).

### kind=instant_answer

- label: short "question, not a goal" UI line (user language)
- answer: useful direct answer — or short safe refusal/redirect under Safety
- goal_suggestions: exactly 2–4 related Facio projects (sequences over time)
- domain: same controlled vocab as path (cooking|…|other) for Q&A demand
- path: empty stub (not a real plan)

### kind=path

{_PATH_FIELDS}

## FCT / quality

- Always fill title + summary on path create (reference intents: carbonara, \
  push-ups → narrative must be visible immediately).
- Always fill cycle + full days[] skeleton on create (reference defaults above).
- Push-ups / fitness week: days must mix train and rest — rest days are real \
  days with kind=rest (light mobility OK), not identical "do sets" days.
- Carbonara: cycle.horizon_days=1, one cook_session day.
- Carbonara cook step: TimerStack required (pasta alert + stir/check nudges); \
  shopping uses checklist, not timers.
- Push-ups train steps: Counter required (reps/sets, current=0); rest → stub.
- First action executable today; honest estimate_min, ideally ≤ 30–60 min.
- Soft cap ≤ 8–12 actions; prefer checklist over many buy-micro-steps.
- Cooking: shopping group + cook how-to in detail; not titles only.
- Prefer a few strong steps over a long todo dump.
- When days[] exist, action titles must not repeat day numbers \
  ("день 2", "day 3") — structure lives in days[] + day_offset.

Do not chat. JSON fields only.
"""

_REFINE_SYSTEM = f"""\
You refine an existing Facio Path from the user's clarification batch.
Return Path JSON only (not the create kind-union).

{_SAFETY}

{_WIRE_SENTINELS}

The user payload has:
- current_state: existing Path JSON
- answers[]: {{question_id, value}} for this round (may be empty)
- comment: optional free-text for the whole round (may be null)

Rules:
- Apply ALL answers and the comment in ONE pass — do not ignore any.
- Do NOT invent constraints/slots the user did not provide.
- If clarify changes the contract → update title, summary, outcome, \
  success_criteria, horizon, and paraphrase explicitly.
- Keep title + summary non-empty and useful after refine.
- Keep cycle + days coherent: if horizon_days changes, rewrite days[] and \
  action day_offset to match; preserve train/rest mix for fitness weeks.
- Preserve action/group ids when the step is the same; do not reshuffle \
  the whole path without cause. New/replaced steps may get new ids.
- Keep every action.why non-empty and meaningful.
- questions[]: only still-useful clarifies (0 or 2–4, max 4); else [].
- Soft cap ≤ 8–12 actions; first remaining step still doable soon.
- Match user language.

{_PATH_FIELDS}
"""

_REPAIR_SYSTEM = f"""\
You repair / recompute a Facio Path for the given reason.
Return Path JSON only.

{_SAFETY}

## Playbooks (by reason)

- illness / sick → reduce load, shift day_offset later; keep ids for done work
- no time → shrink to minimal viable next steps (fewer actions, shorter detail)
- too hard → simplify detail/checklist; never shame
- always preserve completed progress via the same action ids where the step remains

Also:
- Every action.why stays non-empty.
- Soft cap ≤ 8–12 actions; first pending step should be doable soon.
- Do not invent constraints the user did not state.
- Match user language.

{_PATH_FIELDS}
"""

# Compact few-shots — validated by parse_create_response in messages_for_create.
# Unused create branch is an empty stub (wire schema forbids JSON null).
_EMPTY_INSTANT_STUB: dict[str, Any] = {
    "label": "",
    "answer": "",
    "goal_suggestions": [],
    "domain": "other",
}
_EMPTY_PATH_STUB: dict[str, Any] = {
    "title": "",
    "summary": "",
    "outcome": "",
    "paraphrase": "",
    "success_criteria": "",
    "horizon": "",
    "domain": "other",
    "tags": [],
    "cycle": {
        "index": 1,
        "horizon_days": 1,
        "status": "draft",
        "goal_for_cycle": "",
    },
    "days": [],
    "groups": [],
    "actions": [],
    "questions": [],
    "resources": [],
    "milestones": [],
}

_EMPTY_COUNTER_STUB: dict[str, Any] = {
    "label": "",
    "target": -1,
    "current": 0,
    "step": 1,
}

_FEWSHOT_PATH_INTENT = "Приготовить карбонару"
_FEWSHOT_PATH: dict[str, Any] = {
    "kind": "path",
    "path": {
        "title": "Карбонара на ужин",
        "summary": (
            "За один вечер купим продукты и приготовим классическую "
            "карбонару без сливок. Сначала покупки, потом готовка "
            "по шагам — около часа с магазином."
        ),
        "outcome": "Приготовить карбонару дома",
        "paraphrase": "Ок — ведём к: карбонара на ужин",
        "success_criteria": "Тарелка карбонары съедена сегодня вечером",
        "horizon": "1 вечер, ~60–90 мин с покупками",
        "domain": "cooking",
        "tags": ["pasta", "dinner", "carbonara"],
        "cycle": {
            "index": 1,
            "horizon_days": 1,
            "status": "draft",
            "goal_for_cycle": "Карбонара на столе сегодня вечером",
        },
        "days": [
            {
                "day_index": 0,
                "kind": "cook_session",
                "title": "Вечер готовки",
                "summary": "Покупки и классическая карбонара за один заход.",
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
                "why": "Без гуанчиале, яиц и сыра блюдо не собрать",
                "detail": "Магазин рядом; бери гуанчиале или панчетту, не бекон.",
                "estimate_min": 30,
                "day_offset": 0,
                "sort": 0,
                "group_id": "shop",
                "checklist_items": [
                    {"id": "eggs", "title": "яйца", "done": False, "sort": 0},
                    {
                        "id": "guanciale",
                        "title": "гуанчиале / панчетта",
                        "done": False,
                        "sort": 1,
                    },
                    {
                        "id": "pecorino",
                        "title": "пекорино или пармезан",
                        "done": False,
                        "sort": 2,
                    },
                    {
                        "id": "pasta",
                        "title": "спагетти",
                        "done": False,
                        "sort": 3,
                    },
                ],
                "timers": [],
                "counter": dict(_EMPTY_COUNTER_STUB),
            },
            {
                "id": "cook",
                "title": "Приготовить карбонару",
                "why": "Это и есть цель вечера — довести блюдо до тарелки",
                "detail": (
                    "Обжарь гуанчиале. Свари пасту al dente. Смешай желтки "
                    "с тёртым сыром. Сними с огня, соедини пасту с жиром, "
                    "добавь яично-сырную смесь, быстро мешай. Без сливок."
                ),
                "estimate_min": 40,
                "day_offset": 0,
                "sort": 1,
                "group_id": "cook",
                "checklist_items": [],
                "timers": [
                    {
                        "id": "guanciale",
                        "title": "Обжарить гуанчиале",
                        "duration_sec": 480,
                        "signal": "nudge",
                        "parallel_group": "",
                    },
                    {
                        "id": "pasta",
                        "title": "Лапша al dente",
                        "duration_sec": 540,
                        "signal": "alert",
                        "parallel_group": "boil",
                    },
                    {
                        "id": "stir1",
                        "title": "Помешать пасту",
                        "duration_sec": 120,
                        "signal": "nudge",
                        "parallel_group": "boil",
                    },
                    {
                        "id": "stir2",
                        "title": "Помешать ещё раз",
                        "duration_sec": 300,
                        "signal": "nudge",
                        "parallel_group": "boil",
                    },
                ],
                "counter": dict(_EMPTY_COUNTER_STUB),
            },
        ],
        "questions": [
            {
                "id": "meat",
                "prompt": "Какое мясо возьмёте?",
                "options": ["гуанчиале", "панчетта", "что найду"],
            },
            {
                "id": "servings",
                "prompt": "На сколько порций?",
                "options": ["1", "2", "4"],
            },
        ],
        "resources": [],
        "milestones": [],
    },
    "instant_answer": dict(_EMPTY_INSTANT_STUB),
}

_FEWSHOT_FITNESS_INTENT = "Хочу научиться делать 30 отжиманий"
_FEWSHOT_FITNESS: dict[str, Any] = {
    "kind": "path",
    "path": {
        "title": "К 30 отжиманиям — неделя 1",
        "summary": (
            "За ~6–8 недель дойдём к 30 отжиманиям. Эта неделя — база: "
            "четыре короткие силовые и три дня отдыха с лёгкой мобилити."
        ),
        "outcome": "Заложить базу к 30 отжиманиям",
        "paraphrase": "Ок — ведём к: 30 отжиманий, неделя базы",
        "success_criteria": "Закрыты 4 силовых дня недели без срыва программы",
        "horizon": "7 дней, ~15–20 мин в силовые",
        "domain": "fitness",
        "tags": ["push-ups", "strength"],
        "cycle": {
            "index": 1,
            "horizon_days": 7,
            "status": "draft",
            "goal_for_cycle": "Неделя базы: привыкнуть к объёму",
        },
        "days": [
            {
                "day_index": 0,
                "kind": "train",
                "title": "Силовая A",
                "summary": "Короткие подходы отжиманий.",
            },
            {
                "day_index": 1,
                "kind": "rest",
                "title": "Отдых + мобилити",
                "summary": "Восстановление, без силовых подходов.",
            },
            {
                "day_index": 2,
                "kind": "train",
                "title": "Силовая B",
                "summary": "Повторяем объём спокойно.",
            },
            {
                "day_index": 3,
                "kind": "rest",
                "title": "Отдых",
                "summary": "Лёгкая мобилити, мышцы восстанавливаются.",
            },
            {
                "day_index": 4,
                "kind": "train",
                "title": "Силовая C",
                "summary": "Третья силовая недели.",
            },
            {
                "day_index": 5,
                "kind": "rest",
                "title": "Отдых",
                "summary": "Спокойный день без нагрузки.",
            },
            {
                "day_index": 6,
                "kind": "train",
                "title": "Силовая D",
                "summary": "Закрываем неделю короткими подходами.",
            },
        ],
        "groups": [],
        "actions": [
            {
                "id": "d0",
                "title": "Подходы отжиманий",
                "why": "Первый силовой день задаёт ритм недели",
                "detail": "3 подхода по столько, сколько можете с хорошей формой.",
                "estimate_min": 15,
                "day_offset": 0,
                "sort": 0,
                "group_id": "",
                "checklist_items": [],
                "timers": [],
                "counter": {
                    "label": "повторы",
                    "target": 24,
                    "current": 0,
                    "step": 1,
                },
            },
            {
                "id": "d1",
                "title": "Лёгкая мобилити плеч",
                "why": "Отдых — часть программы, не пропуск тренировки",
                "detail": "5–10 минут мягких кругов руками и растяжки груди.",
                "estimate_min": 10,
                "day_offset": 1,
                "sort": 1,
                "group_id": "",
                "checklist_items": [],
                "timers": [],
                "counter": dict(_EMPTY_COUNTER_STUB),
            },
            {
                "id": "d2",
                "title": "Подходы отжиманий",
                "why": "Второй силовой день закрепляет объём",
                "detail": "Снова 3 коротких подхода, без гонки за максимумом.",
                "estimate_min": 15,
                "day_offset": 2,
                "sort": 2,
                "group_id": "",
                "checklist_items": [],
                "timers": [],
                "counter": {
                    "label": "повторы",
                    "target": 24,
                    "current": 0,
                    "step": 1,
                },
            },
            {
                "id": "d3",
                "title": "Прогулка или дыхание",
                "why": "Восстановление даёт следующий силовой день",
                "detail": "Короткая прогулка или 5 минут спокойного дыхания.",
                "estimate_min": 10,
                "day_offset": 3,
                "sort": 3,
                "group_id": "",
                "checklist_items": [],
                "timers": [],
                "counter": dict(_EMPTY_COUNTER_STUB),
            },
            {
                "id": "d4",
                "title": "Подходы отжиманий",
                "why": "Держим ритм недели",
                "detail": "3 подхода; остановитесь, если форма ломается.",
                "estimate_min": 15,
                "day_offset": 4,
                "sort": 4,
                "group_id": "",
                "checklist_items": [],
                "timers": [],
                "counter": {
                    "label": "повторы",
                    "target": 27,
                    "current": 0,
                    "step": 1,
                },
            },
            {
                "id": "d5",
                "title": "Мягкая мобилити",
                "why": "Отдых перед финальной силовой",
                "detail": "Без отжиманий — только лёгкая подвижность.",
                "estimate_min": 8,
                "day_offset": 5,
                "sort": 5,
                "group_id": "",
                "checklist_items": [],
                "timers": [],
                "counter": dict(_EMPTY_COUNTER_STUB),
            },
            {
                "id": "d6",
                "title": "Подходы отжиманий",
                "why": "Закрываем цикл базы",
                "detail": "Последняя силовая недели — спокойный объём.",
                "estimate_min": 15,
                "day_offset": 6,
                "sort": 6,
                "group_id": "",
                "checklist_items": [],
                "timers": [],
                "counter": {
                    "label": "повторы",
                    "target": 30,
                    "current": 0,
                    "step": 1,
                },
            },
        ],
        "questions": [
            {
                "id": "level",
                "prompt": "Сколько отжиманий сейчас получается подряд?",
                "options": ["0–5", "6–15", "16–25", "с колен"],
            },
            {
                "id": "days",
                "prompt": "Сколько дней в неделю реально можете?",
                "options": ["3", "4", "5+"],
            },
        ],
        "resources": [],
        "milestones": [],
    },
    "instant_answer": dict(_EMPTY_INSTANT_STUB),
}

_FEWSHOT_IA_INTENT = "Сколько будет 2 в 100 степени?"
_FEWSHOT_INSTANT: dict[str, Any] = {
    "kind": "instant_answer",
    "path": dict(_EMPTY_PATH_STUB),
    "instant_answer": {
        "label": "Это похоже на вопрос, а не на цель.",
        "answer": (
            "2¹⁰⁰ = 1267650600228229401496703205376"
        ),
        "goal_suggestions": [
            "Научиться считать степени",
            "Изучить бинарную арифметику",
            "Разобрать большие числа в Python",
        ],
        "domain": "learning",
    },
}


def messages_for_create(intent: str) -> list[dict[str, Any]]:
    return [
        {"role": "system", "content": _CREATE_SYSTEM},
        {"role": "user", "content": _FEWSHOT_PATH_INTENT},
        {
            "role": "assistant",
            "content": json.dumps(_FEWSHOT_PATH, ensure_ascii=False),
        },
        {"role": "user", "content": _FEWSHOT_FITNESS_INTENT},
        {
            "role": "assistant",
            "content": json.dumps(_FEWSHOT_FITNESS, ensure_ascii=False),
        },
        {"role": "user", "content": _FEWSHOT_IA_INTENT},
        {
            "role": "assistant",
            "content": json.dumps(_FEWSHOT_INSTANT, ensure_ascii=False),
        },
        {"role": "user", "content": intent},
    ]


def messages_for_refine(
    *,
    current_state: dict[str, Any],
    answers: list[dict[str, str]],
    comment: str | None = None,
) -> list[dict[str, Any]]:
    return [
        {"role": "system", "content": _REFINE_SYSTEM},
        {
            "role": "user",
            "content": json.dumps(
                {
                    "current_state": current_state,
                    "answers": answers,
                    "comment": comment,
                },
                ensure_ascii=False,
            ),
        },
    ]


def messages_for_repair(
    *,
    current_state: dict[str, Any],
    reason: str,
    project_status: str,
) -> list[dict[str, Any]]:
    return [
        {"role": "system", "content": _REPAIR_SYSTEM},
        {
            "role": "user",
            "content": json.dumps(
                {
                    "current_state": current_state,
                    "reason": reason,
                    "project_status": project_status,
                },
                ensure_ascii=False,
            ),
        },
    ]


def _empty_to_none(value: Any) -> Any:
    if value == "":
        return None
    return value


def _neg1_to_none(value: Any) -> Any:
    if value == -1:
        return None
    return value


def normalize_path_wire_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Map Anthropic wire sentinels (``""``, ``-1``) to ``None`` for PathState."""
    out = dict(data)

    cycle = out.get("cycle")
    if isinstance(cycle, dict):
        cycle = dict(cycle)
        cycle["goal_for_cycle"] = _empty_to_none(cycle.get("goal_for_cycle"))
        out["cycle"] = cycle

    days = out.get("days")
    if isinstance(days, list):
        normalized_days: list[Any] = []
        for day in days:
            if not isinstance(day, dict):
                normalized_days.append(day)
                continue
            day = dict(day)
            day["title"] = _empty_to_none(day.get("title"))
            day["summary"] = _empty_to_none(day.get("summary"))
            normalized_days.append(day)
        out["days"] = normalized_days

    groups = out.get("groups")
    if isinstance(groups, list):
        normalized_groups: list[Any] = []
        for group in groups:
            if not isinstance(group, dict):
                normalized_groups.append(group)
                continue
            group = dict(group)
            group["description"] = _empty_to_none(group.get("description"))
            normalized_groups.append(group)
        out["groups"] = normalized_groups

    actions = out.get("actions")
    if isinstance(actions, list):
        normalized_actions: list[Any] = []
        for action in actions:
            if not isinstance(action, dict):
                normalized_actions.append(action)
                continue
            action = dict(action)
            action["id"] = _empty_to_none(action.get("id"))
            action["detail"] = _empty_to_none(action.get("detail"))
            action["group_id"] = _empty_to_none(action.get("group_id"))
            action["estimate_min"] = _neg1_to_none(action.get("estimate_min"))
            action["day_offset"] = _neg1_to_none(action.get("day_offset"))
            action["sort"] = _neg1_to_none(action.get("sort"))
            items = action.get("checklist_items")
            if isinstance(items, list):
                normalized_items: list[Any] = []
                for item in items:
                    if not isinstance(item, dict):
                        normalized_items.append(item)
                        continue
                    item = dict(item)
                    item["id"] = _empty_to_none(item.get("id"))
                    normalized_items.append(item)
                action["checklist_items"] = normalized_items
            timers = action.get("timers")
            if isinstance(timers, list):
                normalized_timers: list[Any] = []
                for timer in timers:
                    if not isinstance(timer, dict):
                        normalized_timers.append(timer)
                        continue
                    timer = dict(timer)
                    timer["id"] = _empty_to_none(timer.get("id"))
                    timer["parallel_group"] = _empty_to_none(
                        timer.get("parallel_group")
                    )
                    normalized_timers.append(timer)
                action["timers"] = normalized_timers
            elif timers is None:
                action["timers"] = []
            counter = action.get("counter")
            if isinstance(counter, dict):
                counter = dict(counter)
                counter["label"] = _empty_to_none(counter.get("label"))
                target = counter.get("target", -1)
                if target is None or target == -1:
                    action["counter"] = None
                else:
                    action["counter"] = counter
            normalized_actions.append(action)
        out["actions"] = normalized_actions

    return out


def _is_empty_path_stub(path: Any) -> bool:
    if path is None:
        return True
    if not isinstance(path, dict):
        return False
    title = path.get("title")
    actions = path.get("actions")
    return (not title) and (not actions)


def _is_empty_instant_stub(payload: Any) -> bool:
    if payload is None:
        return True
    if not isinstance(payload, dict):
        return False
    label = payload.get("label")
    answer = payload.get("answer")
    suggestions = payload.get("goal_suggestions") or []
    return (not label) and (not answer) and len(suggestions) == 0


def parse_path_state(raw_response: Any) -> PathState:
    if isinstance(raw_response, PathState):
        return raw_response
    if isinstance(raw_response, str):
        data = json.loads(raw_response)
    elif isinstance(raw_response, dict):
        data = raw_response
    else:
        raise TypeError(
            f"Unexpected raw_response type: {type(raw_response)!r}"
        )
    if isinstance(data, dict):
        data = normalize_path_wire_dict(data)
    return PathState.model_validate(data)


def parse_create_response(raw_response: Any) -> CreateLlmResponse:
    if isinstance(raw_response, CreateLlmResponse):
        return raw_response
    if isinstance(raw_response, str):
        data = json.loads(raw_response)
    elif isinstance(raw_response, dict):
        data = raw_response
    else:
        raise TypeError(
            f"Unexpected raw_response type: {type(raw_response)!r}"
        )
    if not isinstance(data, dict):
        return CreateLlmResponse.model_validate(data)

    out = dict(data)
    kind = out.get("kind")
    # Wire schema requires both branches as objects; drop the unused stub/null
    # before Pydantic validates the discriminated union.
    if kind == "path":
        out["instant_answer"] = None
        path = out.get("path")
        if isinstance(path, dict):
            out["path"] = normalize_path_wire_dict(path)
    elif kind == "instant_answer":
        out["path"] = None
    else:
        # Defensive: still normalize if a path object is present.
        path = out.get("path")
        if isinstance(path, dict) and not _is_empty_path_stub(path):
            out["path"] = normalize_path_wire_dict(path)
        if _is_empty_instant_stub(out.get("instant_answer")):
            out["instant_answer"] = None
        if _is_empty_path_stub(out.get("path")):
            out["path"] = None

    return CreateLlmResponse.model_validate(out)
