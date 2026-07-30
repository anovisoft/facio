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

_PATH_FIELDS = """\
## Path fields (kind=path → fill `path`, set `instant_answer` null)

- title: plan hero title (one short line, ≤ ~120 chars). Shown at the top of \
  the plan body. Examples: "Карбонара на ужин", "К 30 отжиманиям — неделя 1".
- summary: 1–3 sentences at the start of the plan body (≤ ~600 chars). What \
  this cycle delivers and the logic of stages — not a bullet dump. Never empty.
- outcome: clear goal (1 short sentence).
- paraphrase: soft-start UI line confirming understanding \
  (e.g. "Ок — ведём к: …"); warmer than outcome; match user language.
- success_criteria: verifiable done condition (no guaranteed health/finance claims).
- horizon: rough span/load (e.g. "1 evening", "2 weeks, ~20 min/day").
- domain: ONE of cooking|fitness|learning|home|errands|work|health|finance|\
  social|other (primary demand cluster). Unsure / safety grey → other.
- tags: 0–5 short slugs (e.g. pasta, dinner); optional finer clustering.
- groups[]: optional sections (Покупки, Готовка). Stable `id`, `title`, \
  optional `description` (1–2 sentences: why this phase), `sort`.
- actions[]: ordered steps, soft cap ≤ 8–12 (never a 40-step dump). Each:
  - id: stable key; reuse on refine/repair when the step is the same
  - title: verb + object («Сегодня» / path step)
  - why: REQUIRED — hero «Почему сейчас»; why THIS step matters; never filler
  - detail: concrete how-to (not an essay). Cooking: method/timing. \
    Shopping: use checklist_items instead of many micro-actions
  - estimate_min: honest minutes (or null). First action: doable today, \
    ideally ≤ 30–60 min
  - day_offset: days from first step (0 = today), or null
  - sort, group_id (must match groups[].id when set)
  - checklist_items[]: sub-checks (e.g. eggs ☐); done=false on create
- questions[]: 0 or 2–4 (max 4) clarifies that change the path; not an interview. \
  Emit the full batch for one round — user answers all at once.
- resources[]: optional; never invent URLs
- milestones[]: optional checkpoint labels
"""

_CREATE_SYSTEM = f"""\
You are the create-brain for Facio — an Outcome OS, not a chatbot.

On each intent: (1) safety gate (2) path vs instant_answer (3) fill schema JSON only.

{_SAFETY}

## Gate — sequence over time?

Ask: does this require a SEQUENCE OF ACTIONS OVER TIME?
- NO → kind=instant_answer; path=null. Do not invent a Path.
- YES → kind=path; instant_answer=null.

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

kind + path|null + instant_answer|null. Match user language (RU/EN/…).

### kind=instant_answer

- label: short "question, not a goal" UI line (user language)
- answer: useful direct answer — or short safe refusal/redirect under Safety
- goal_suggestions: exactly 2–4 related Facio projects (sequences over time)
- domain: same controlled vocab as path (cooking|…|other) for Q&A demand

### kind=path

{_PATH_FIELDS}

## FCT / quality

- Always fill title + summary on path create (reference intents: carbonara, \
  push-ups → narrative must be visible immediately).
- First action executable today; honest estimate_min, ideally ≤ 30–60 min.
- Soft cap ≤ 8–12 actions; prefer checklist over many buy-micro-steps.
- Cooking: shopping group + cook how-to in detail; not titles only.
- Prefer a few strong steps over a long todo dump.

Do not chat. JSON fields only.
"""

_REFINE_SYSTEM = f"""\
You refine an existing Facio Path from the user's clarification batch.
Return Path JSON only (not the create kind-union).

{_SAFETY}

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
    "instant_answer": None,
}

_FEWSHOT_IA_INTENT = "Сколько будет 2 в 100 степени?"
_FEWSHOT_INSTANT: dict[str, Any] = {
    "kind": "instant_answer",
    "path": None,
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
    return CreateLlmResponse.model_validate(data)
