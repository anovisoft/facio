"""LLM prompt builders and PathState / create-response parsing."""

from __future__ import annotations

import json
from typing import Any

from app.schemas.create_response import (
    CREATE_GATE_SCHEMA,
    CREATE_RESPONSE_SCHEMA,
    CreateGateResponse,
    CreateLlmResponse,
    InstantAnswerPayload,
    PathStartSurface,
)
from app.schemas.path_state import (
    PATH_RESPONSE_SCHEMA,
    PLUGINS_MATERIALIZE_SCHEMA,
    ActionPluginsMaterialize,
    PathState,
    normalize_stepper_beats,
)

__all__ = [
    "CREATE_GATE_SCHEMA",
    "CREATE_RESPONSE_SCHEMA",
    "PATH_RESPONSE_SCHEMA",
    "PLUGINS_MATERIALIZE_SCHEMA",
    "messages_for_create",
    "messages_for_create_gate",
    "messages_for_create_path",
    "messages_for_materialize_plugins",
    "messages_for_next_cycle",
    "messages_for_refine",
    "messages_for_repair",
    "parse_create_gate",
    "parse_create_response",
    "parse_path_state",
    "parse_plugins_materialize",
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
  day title/summary, group description, checklist id)
- missing optional int → -1 (estimate_min, sort; never for a real day_offset)
- unused create branch → empty stub object (not null): see Response shape

Create #2 / refine Path wire does NOT include timers/timeline/interval_plan/\
counter/stepper objects — only plugin_hints[]. Full plugins are a later call (#3).
"""

_PLUGIN_WIRE_SENTINELS = """\
## Plugin wire sentinels (materialize #3 only)

- no counters on a step → counter stub \
  {label:"", target:-1, current:0, step:1} (not null)
- no timers → timers: []
- no timeline → timeline stub {duration_sec:-1, markers:[]} (not null)
- no interval_plan → interval_plan stub {segments:[]} (not null)
- no stepper → stepper stub {beats:[]} (not null)
- timer id / parallel_group missing → ""
- stepper beat: unused counter → {label:"", target:-1, current:0, step:1}; \
  unused duration_sec → -1; unused signal → "nudge" (ignored when absent)
"""

_PATH_FIELDS = """\
## Path fields (Path JSON root — no kind wrapper)

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
  - horizon_days: integer length of THIS cycle — HARD MAX 14, target 7 for \
    fitness/push-ups (one training week)
      * cooking / one-dish (carbonara) → 1
      * fitness / push-ups toward a rep goal → 7 (ONE week). NEVER emit a \
        4–6 week / 30–45 day horizon as a single cycle — a multi-week \
        aspiration belongs in `summary`/`outcome` ("~6–8 недель к цели, эта \
        неделя — база"); the NEXT weeks are a later cycle, not padding on \
        this one. A cycle over 14 days is invalid and will be rejected.
      * other domains: pick a short honest horizon (1–14 typical)
  - status: "draft" on create/refine; never invent completed
  - goal_for_cycle: short goal for this cycle, or "" if none
- days[]: REQUIRED explicit day map for the cycle (not only day_offset):
  - day_index: 0 .. horizon_days-1 (include every day in the skeleton)
  - kind: train | rest | cook_session | other
      * carbonara / cooking session → one day kind=cook_session
      * push-ups week → mix train and rest (NOT 7 identical train days)
  - title / summary: short labels or "" (e.g. "Силовая A", "Отдых + мобилити")
- groups[]: optional sections (Покупки, Подготовка, Готовка). Stable `id`, \
  `title`, description (1–2 sentences or ""), `sort`.
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
  - checklist_items[]: shopping / binary prep / mise only (eggs ☐, cut meat, \
    grate cheese). done=false on create; id or "". NEVER use checklist for \
    gym sets («Подход 1/2/3») — that is stepper beats, not checkboxes.
  - plugin_hints[]: short tool announcements ONLY (no plugin objects here):
      * "timeline" — ONE session axis with markers (carbonara COOK SESSION \
        MUST). Stir / "помешать" = markers on the axis, NOT peer timers. \
        Timeline markers are ONLY clock-critical session beats (heat/sear \
        progress, pasta in water, emulsify, plate). FORBIDDEN: knife-work / \
        mise / "нарезать" / grate / mix yolks as timeline markers — those \
        belong on a PRIOR prep checklist action with plugin_hints=[].
      * "timers" — isolated manual Start wait with NO session axis \
        (e.g. dough rest). Do NOT combine with timeline on the same action.
      * "stepper" — strength session: measure/work/rest beats with counters \
        on work/measure and rest timers between. ONE train day = ONE action \
        with ["stepper"] (merge former max-test + volume into one session). \
        FORBIDDEN: checklist «Подход N» + a bare action-level "counter".
      * "interval" — HIIT / circuit timed purely in seconds (Tabata-style). \
        Prefer stepper when the session is sets + rest by reps, not seconds.
      * "counter" — a SINGLE dose outside a set series (rare). Inside \
        strength sets, put counters on stepper beats, not on the action.
      * [] when no tools (shopping, prep/mise, rest mobility)
      Choose the right object: cook session → timeline; prep/mise → \
      checklist + []; strength sets → stepper; timed HIIT → interval; \
      shopping → checklist. timeline XOR timers (never both). If stepper \
      is present, do NOT also hint bare "counter" for the same sets.
  - Do NOT emit timers[], timeline, interval_plan, counter, or stepper \
    objects on Path — hints only.
- questions[]: 0 or 2–4 (max 4) clarifies that change the path; not an interview. \
  Emit the full batch for one round — user answers all at once.
- Do NOT emit resources[] or milestones[] (server defaults to []).
"""

_PATH_QUALITY = """\
## FCT / quality

- Always fill title + summary (reference intents: carbonara, push-ups → \
  narrative must be visible immediately).
- Always fill cycle + full days[] skeleton (reference defaults above).
- Push-ups / fitness week: days must mix train and rest — rest days are real \
  days with kind=rest (light mobility OK), not identical "do sets" days.
- Never emit a hollow tail: days[] must not run past the last day that has \
  an action attached. Do not pad with empty rest days to make the cycle \
  sound longer — a short honest horizon beats a hollow multi-week shell.
- Carbonara: cycle.horizon_days=1, one cook_session day.
- Cooking / carbonara Path shape (prep ≠ timeline axis):
    1) shop — checklist, plugin_hints=[]
    2) prep / mise — checklist action(s) BEFORE the cook session \
       (cut meat, grate cheese, mix yolks…); plugin_hints=[] — NEVER \
       timeline or timers on mise
    3) cook session — ONE action, plugin_hints=["timeline"] only \
       (no "timers" on the same step; stir markers live on the axis). \
       Timeline t=0 = heat / water / sear-on-axis — NOT knife-work.
- Push-ups / strength train day: ONE session action with plugin_hints \
  ["stepper"] — not two actions (max + volume), not checklist approaches, \
  not a lone action-level counter. Rest days → [].
- First action executable today; honest estimate_min, ideally ≤ 30–60 min.
- Soft cap ≤ 8–12 actions; prefer checklist over many buy-micro-steps.
- Cooking: shopping + prep/mise groups + cook how-to in detail; not titles only.
- Prefer a few strong steps over a long todo dump.
- When days[] exist, action titles must not repeat day numbers \
  ("день 2", "day 3") — structure lives in days[] + day_offset.
"""

_CREATE_GATE_SYSTEM = f"""\
You are the create-gate for Facio — an Outcome OS, not a chatbot.

Decide path vs instant_answer. When path: also emit a slim START SURFACE \
(meaning + questions) — NOT a full Path / plugins / actions.

{_SAFETY}

## Gate — sequence over time?

Ask: does this require a SEQUENCE OF ACTIONS OVER TIME?
- NO → kind=instant_answer; fill instant_answer fully; path_start = empty stub.
- YES → kind=path; fill path_start; instant_answer = empty stub \
  (label="", answer="", goal_suggestions=[], domain="other").

Clear instant_answer: one-shot math/facts (2^100), FX rates, translate a word, \
pure Q&A with no multi-step pursuit.
Clear path: buy a car, learn Python, cook carbonara, write a thesis.

### Grey zones

- One-shot habit/reminder ("remind me to call") → instant_answer, or a tiny \
  path of 1–2 steps — never a multi-week novel (prefer kind=path only if they \
  clearly want a short sequence).
- "What should I cook today?" if they want to make it → kind=path.
- Career/life advice with no actionable sequence → instant_answer + \
  goal_suggestions; no pseudo-therapy path.
- Unsure whether a sequence-over-time exists → prefer instant_answer + \
  suggestions, unless they clearly want to pursue an outcome.

## Response shape

Always emit `kind`, `instant_answer`, and `path_start` (never JSON null). \
Match user language.

### kind=instant_answer

- label: short "question, not a goal" UI line (user language)
- answer: useful direct answer — or short safe refusal/redirect under Safety
- goal_suggestions: exactly 2–4 related Facio projects (sequences over time)
- domain: cooking|fitness|learning|home|errands|work|health|finance|social|other
- path_start: empty stub \
  (paraphrase="", title="", summary="", questions=[], outline_days=[])

### kind=path

- instant_answer must be the empty stub above
- path_start (shown to user immediately; full Path is a later call):
  - paraphrase: soft-start line (e.g. "Ок — ведём к: …")
  - title: short plan hero (≤ ~120 chars)
  - summary: 1–3 sentences draft of what the cycle delivers (never empty)
  - questions: 0 or 2–4 clarifies that change the plan (full batch; not interview)
    Each: id, prompt, options[] (2–4 chips; user may still type free text)
  - outline_days: rough day TITLES for THIS cycle only — ≤7 short strings \
    (fitness/push-ups week → exactly 7, one per day; carbonara → 1), \
    e.g. ["Вечер готовки"] or ["Силовая A","Отдых",…]. If the goal spans \
    many weeks, say so in `summary` ("неделя 1 из ~6–8"/"часть 6–8-недельной \
    программы") — do NOT lengthen outline_days to cover multiple weeks; \
    next weeks are a later cycle. NO plugins, NO actions, NO kind enums — \
    titles only. Empty [] if unsure.

Do not chat. JSON fields only.
"""

_CREATE_PATH_SYSTEM = f"""\
You are the create-path brain for Facio. The gate already decided kind=path \
and showed the user a slim start surface (paraphrase/title/summary/questions).
Emit Path JSON only (root object — no kind / instant_answer wrapper).

Align with the start surface the user already saw: keep title/summary/paraphrase \
close; reuse question ids/prompts when still useful; expand into full cycle, \
days, actions, and plugin_hints (NOT full plugin payloads).

{_SAFETY}

{_WIRE_SENTINELS}

{_PATH_FIELDS}

{_PATH_QUALITY}

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
- Never grow horizon_days past 14 for a single cycle (fitness target 7); a \
  longer program is future cycles, not padding on this one. Do not leave a \
  hollow tail of empty rest days past the last real action.
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

## Playbooks (by reason / intent)

- intent=shift (or illness / sick) → push the blocked day's actions to a
  later day_offset (usually +1); keep ids and content otherwise unchanged
- intent=lighten (or no time / too hard) → shrink today's actions to the
  minimal viable next steps (fewer actions, shorter detail, lower volume
  in titles+detail); never shame. Emit plugin_hints only — full plugin
  objects (stepper/counter/…) are rematerialized separately after apply
- intent=rest → replace today's pending actions with a single light rest /
  recovery action for that day_offset; keep other days untouched. Emit
  plugin_hints only when a tool is needed; payloads rematerialize later
- always preserve completed progress via the same action ids where the step remains
- never move a day_offset backward relative to the project's cycle_anchor
  (do not unlock execute for a day that hasn't opened yet)

Also:
- Every action.why stays non-empty.
- Soft cap ≤ 8–12 actions; first pending step should be doable soon.
- Do not invent constraints the user did not state.
- Match user language.
- Set ``paraphrase`` to a short one-line "what changed" summary of THIS
  repair (e.g. "Moved today's workout to tomorrow" / "Swapped today for a
  rest day") — it is shown to the user as a confirmation, not the plan intro.

{_PATH_FIELDS}
"""

_NEXT_CYCLE_SYSTEM = f"""\
You build the NEXT Facio cycle (N+1) from the prior cycle plan + structured \
results. Return Path JSON only (same shape as create #2 — plugin_hints, \
NO plugin objects).

{_SAFETY}

{_WIRE_SENTINELS}

The user payload has:
- prior_state: Path JSON of the cycle that just finished
- cycle_result: structured summary \
  (completed_steps, skipped_steps, partial, partial_notes, counters_snapshot, \
  user_comment)
- answers[] / comment: optional clarify batch for N+1 (may be empty)
- next_index: integer cycle index to emit (MUST use this)
- continue_kind: "next" (multi-day / fitness) or "repeat" (cook / horizon 1)

Rules:
- Emit a FULL new cycle Path for THIS short cycle only — not the whole \
  multi-week aspiration. Narrative ("~6–8 weeks to 30") stays in summary; \
  cycle.horizon_days stays short (fitness target 7, hard max 14; cook = 1).
- cycle.index MUST equal next_index; cycle.status = "active".
- Progress from results: if the user completed most train days → slightly \
  increase volume / difficulty; if partial / many skips → hold or ease; \
  respect counters_snapshot facts when present.
- continue_kind=repeat (carbonara / horizon 1): build a sensible REPEAT \
  session (same dish or light variation), horizon_days=1, cook_session day. \
  Do not invent a multi-week cooking program.
- continue_kind=next (fitness): week N+1 with train/rest mix; reuse stable \
  structure; new action ids are fine (fresh cycle).
- Apply answers + comment in ONE pass when present.
- questions[]: 0 or 2–4 still-useful clarifies for later; often [] after \
  a finished cycle.
- Soft cap ≤ 8–12 actions; plugin_hints as on create \
  (cook session → timeline; prep/mise → []; shopping → []; \
  strength → stepper). On cook repeat: keep prep checklist outside \
  the timeline axis (no mise-as-first-marker).
- title/summary/paraphrase non-empty; match user language.
- Never grow past horizon caps; no hollow rest tails.

{_PATH_FIELDS}

{_PATH_QUALITY}
"""

# Compact few-shots. Path bodies validated by parse_path_state; gate by
# parse_create_gate. Combined _FEWSHOT_PATH / _FEWSHOT_FITNESS kept for tests.
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

_EMPTY_TIMELINE_STUB: dict[str, Any] = {
    "duration_sec": -1,
    "markers": [],
}

_EMPTY_INTERVAL_STUB: dict[str, Any] = {
    "segments": [],
}

_EMPTY_STEPPER_STUB: dict[str, Any] = {
    "beats": [],
}

_EMPTY_BEAT_COUNTER_STUB: dict[str, Any] = {
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
            "За один вечер купим продукты, сделаем mise en place и "
            "приготовим классическую карбонару без сливок. Покупки → "
            "подготовка → готовка по таймлайну — около часа с магазином."
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
                "summary": "Покупки, mise и классическая карбонара за один заход.",
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
                "id": "prep",
                "title": "Подготовка",
                "description": "Mise en place до включения плиты.",
                "sort": 1,
            },
            {
                "id": "cook",
                "title": "Готовка",
                "description": "Собрать блюдо по классическому методу.",
                "sort": 2,
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
                "plugin_hints": [],
            },
            {
                "id": "prep",
                "title": "Подготовить продукты",
                "why": "Mise до плиты — на таймлайне готовки уже только жар и вода",
                "detail": (
                    "Нарежь гуанчиале/карбонад кубиками, натри сыр, "
                    "смешай желтки с сыром. Всё готово до включения огня."
                ),
                "estimate_min": 15,
                "day_offset": 0,
                "sort": 1,
                "group_id": "prep",
                "checklist_items": [
                    {
                        "id": "cut_meat",
                        "title": "нарезать гуанчиале",
                        "done": False,
                        "sort": 0,
                    },
                    {
                        "id": "grate_cheese",
                        "title": "натереть сыр",
                        "done": False,
                        "sort": 1,
                    },
                    {
                        "id": "mix_yolks",
                        "title": "смешать желтки с сыром",
                        "done": False,
                        "sort": 2,
                    },
                ],
                "plugin_hints": [],
            },
            {
                "id": "cook",
                "title": "Приготовить карбонару",
                "why": "Это и есть цель вечера — довести блюдо до тарелки",
                "detail": (
                    "Обжарь гуанчиале. Свари пасту al dente. Сними с огня, "
                    "соедини пасту с жиром, добавь яично-сырную смесь, "
                    "быстро мешай. Без сливок."
                ),
                "estimate_min": 25,
                "day_offset": 0,
                "sort": 2,
                "group_id": "cook",
                "checklist_items": [],
                "plugin_hints": ["timeline"],
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
                "title": "Силовая сессия",
                "why": "Первый силовой день задаёт ритм недели",
                "detail": (
                    "Замер → отдых → подходы с отдыхом между. Один сеанс."
                ),
                "estimate_min": 20,
                "day_offset": 0,
                "sort": 0,
                "group_id": "",
                "checklist_items": [],
                "plugin_hints": ["stepper"],
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
                "plugin_hints": [],
            },
            {
                "id": "d2",
                "title": "Силовая сессия",
                "why": "Второй силовой день закрепляет объём",
                "detail": "Снова замер и подходы — без гонки за максимумом.",
                "estimate_min": 20,
                "day_offset": 2,
                "sort": 2,
                "group_id": "",
                "checklist_items": [],
                "plugin_hints": ["stepper"],
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
                "plugin_hints": [],
            },
            {
                "id": "d4",
                "title": "Силовая сессия",
                "why": "Держим ритм недели",
                "detail": "Подходы с хорошей формой; остановитесь, если ломается.",
                "estimate_min": 20,
                "day_offset": 4,
                "sort": 4,
                "group_id": "",
                "checklist_items": [],
                "plugin_hints": ["stepper"],
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
                "plugin_hints": [],
            },
            {
                "id": "d6",
                "title": "Силовая сессия",
                "why": "Закрываем цикл базы",
                "detail": "Последняя силовая недели — спокойный объём.",
                "estimate_min": 20,
                "day_offset": 6,
                "sort": 6,
                "group_id": "",
                "checklist_items": [],
                "plugin_hints": ["stepper"],
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

_EMPTY_PATH_START_STUB: dict[str, Any] = {
    "paraphrase": "",
    "title": "",
    "summary": "",
    "questions": [],
    "outline_days": [],
}

_FEWSHOT_GATE_PATH: dict[str, Any] = {
    "kind": "path",
    "instant_answer": dict(_EMPTY_INSTANT_STUB),
    "path_start": {
        "paraphrase": "Ок — ведём к: карбонара на ужин",
        "title": "Карбонара на ужин",
        "summary": (
            "За один вечер купим продукты, сделаем mise и приготовим "
            "классическую карбонару без сливок."
        ),
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
        "outline_days": ["Вечер готовки"],
    },
}
_FEWSHOT_GATE_INSTANT: dict[str, Any] = {
    "kind": "instant_answer",
    "instant_answer": dict(_FEWSHOT_INSTANT["instant_answer"]),
    "path_start": dict(_EMPTY_PATH_START_STUB),
}

_MATERIALIZE_SYSTEM = f"""\
You fill Facio action plugins after the user started the plan.
Emit ONLY {{"actions":[...]}} — each item has action_id + plugin payloads.
Do NOT rewrite the Path skeleton (no title/days/questions).

{_SAFETY}

{_PLUGIN_WIRE_SENTINELS}

## Fields per action

- action_id: MUST match an id from the hinted actions list
- timers[]: simple TimerStack {{id|"", title, duration_sec≥1, signal, \
  parallel_group|""}}. Empty [] when unused.
- timeline: ALWAYS present. Real: duration_sec≥1 + markers[] of \
  {{sec, title, signal}} (sec = absolute at_sec). Absent → \
  {{duration_sec:-1, markers:[]}}. Carbonara cook session: clock axis \
  starting at heat/water/sear-on-axis (e.g. «Паста в воду» / «Жар»), \
  with stir nudges + alert done — NOT peer stir timers as the primary \
  shape. FORBIDDEN: invent mise / knife-work markers («нарезать», \
  grate, mix yolks) on a timeline hint — mise belongs on a prior \
  checklist action with no timeline. First marker MUST NOT be cut/chop.
- interval_plan: ALWAYS present. Real: segments[] of {{sec, title, signal}} \
  (sec = segment duration_sec). Absent → {{segments:[]}}. Timed HIIT only.
- stepper: ALWAYS present. Real: beats[] of \
  {{id|"", kind: measure|work|rest, title, counter, duration_sec, signal}}. \
  measure/work: MUST emit a real counter (target≥1, current=0, step≥1) — \
  NEVER a stub (target=-1) and NEVER omit counter. duration_sec=-1 on \
  measure/work. \
  rest: duration_sec≥1 + counter stub (target=-1). Absent → {{beats:[]}}. \
  Strength train day: measure → rest → work → rest → work… One action covers \
  the whole session (no separate max + volume actions).
- counter: ALWAYS present. Real: label, target≥1, current=0, step≥1. \
  Absent → {{label:"", target:-1, current:0, step:1}}. Use ONLY for a lone \
  dose outside a set series. If stepper is real, action-level counter MUST \
  be the absent stub.

Honor plugin_hints: timeline → real timeline + timers MUST be []; \
timers → timers[] only when timeline is absent; stepper → real stepper beats \
(+ action counter stub); interval → interval_plan; counter → counter only \
when there is no stepper. Unused shapes → stubs / [].
If hint is timeline: emit ONLY clock-critical session markers; do NOT \
invent prep/mise markers (cut/chop/grate/yolks) — those were checklist \
on a prior action.
NEVER put a real timeline and non-empty timers on the same action.
NEVER turn gym sets into checklist_items or a bare counter without stepper.

Emit one entry per hinted action (all hinted in the cycle for MVP).
Match user language in titles. Do not chat. JSON only.
"""

_FEWSHOT_MATERIALIZE_CARBONARA: dict[str, Any] = {
    "actions": [
        {
            "action_id": "cook",
            "timers": [],
            "counter": dict(_EMPTY_COUNTER_STUB),
            "timeline": {
                "duration_sec": 600,
                "markers": [
                    {"sec": 0, "title": "Жар / мясо на сковороду", "signal": "nudge"},
                    {"sec": 180, "title": "Паста в воду", "signal": "nudge"},
                    {"sec": 360, "title": "Помешать пасту", "signal": "nudge"},
                    {
                        "sec": 480,
                        "title": "Эмульсия и снять с огня",
                        "signal": "nudge",
                    },
                    {"sec": 600, "title": "На тарелки", "signal": "alert"},
                ],
            },
            "interval_plan": dict(_EMPTY_INTERVAL_STUB),
            "stepper": dict(_EMPTY_STEPPER_STUB),
        }
    ]
}

_FEWSHOT_MATERIALIZE_FITNESS: dict[str, Any] = {
    "actions": [
        {
            "action_id": "d0",
            "timers": [],
            "counter": dict(_EMPTY_COUNTER_STUB),
            "timeline": dict(_EMPTY_TIMELINE_STUB),
            "interval_plan": dict(_EMPTY_INTERVAL_STUB),
            "stepper": {
                "beats": [
                    {
                        "id": "m0",
                        "kind": "measure",
                        "title": "Замер: сколько получается",
                        "counter": {
                            "label": "повторы",
                            "target": 15,
                            "current": 0,
                            "step": 1,
                        },
                        "duration_sec": -1,
                        "signal": "nudge",
                    },
                    {
                        "id": "r0",
                        "kind": "rest",
                        "title": "Отдых перед подходами",
                        "counter": dict(_EMPTY_BEAT_COUNTER_STUB),
                        "duration_sec": 300,
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
                        "duration_sec": -1,
                        "signal": "nudge",
                    },
                    {
                        "id": "r1",
                        "kind": "rest",
                        "title": "Отдых",
                        "counter": dict(_EMPTY_BEAT_COUNTER_STUB),
                        "duration_sec": 120,
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
                        "duration_sec": -1,
                        "signal": "nudge",
                    },
                    {
                        "id": "r2",
                        "kind": "rest",
                        "title": "Отдых",
                        "counter": dict(_EMPTY_BEAT_COUNTER_STUB),
                        "duration_sec": 120,
                        "signal": "nudge",
                    },
                    {
                        "id": "w3",
                        "kind": "work",
                        "title": "Подход 3",
                        "counter": {
                            "label": "повторы",
                            "target": 12,
                            "current": 0,
                            "step": 1,
                        },
                        "duration_sec": -1,
                        "signal": "alert",
                    },
                ],
            },
        },
        {
            "action_id": "d2",
            "timers": [],
            "counter": dict(_EMPTY_COUNTER_STUB),
            "timeline": dict(_EMPTY_TIMELINE_STUB),
            "interval_plan": dict(_EMPTY_INTERVAL_STUB),
            "stepper": {
                "beats": [
                    {
                        "id": "m0",
                        "kind": "measure",
                        "title": "Короткий замер",
                        "counter": {
                            "label": "повторы",
                            "target": 12,
                            "current": 0,
                            "step": 1,
                        },
                        "duration_sec": -1,
                        "signal": "nudge",
                    },
                    {
                        "id": "r0",
                        "kind": "rest",
                        "title": "Отдых",
                        "counter": dict(_EMPTY_BEAT_COUNTER_STUB),
                        "duration_sec": 180,
                        "signal": "nudge",
                    },
                    {
                        "id": "w1",
                        "kind": "work",
                        "title": "Подход 1",
                        "counter": {
                            "label": "повторы",
                            "target": 10,
                            "current": 0,
                            "step": 1,
                        },
                        "duration_sec": -1,
                        "signal": "nudge",
                    },
                    {
                        "id": "r1",
                        "kind": "rest",
                        "title": "Отдых",
                        "counter": dict(_EMPTY_BEAT_COUNTER_STUB),
                        "duration_sec": 90,
                        "signal": "nudge",
                    },
                    {
                        "id": "w2",
                        "kind": "work",
                        "title": "Подход 2",
                        "counter": {
                            "label": "повторы",
                            "target": 10,
                            "current": 0,
                            "step": 1,
                        },
                        "duration_sec": -1,
                        "signal": "alert",
                    },
                ],
            },
        },
    ]
}


def messages_for_create_gate(intent: str) -> list[dict[str, Any]]:
    """Phase 1: slim schema — kind + instant_answer + path_start surface."""
    return [
        {"role": "system", "content": _CREATE_GATE_SYSTEM},
        {"role": "user", "content": _FEWSHOT_PATH_INTENT},
        {
            "role": "assistant",
            "content": json.dumps(_FEWSHOT_GATE_PATH, ensure_ascii=False),
        },
        {"role": "user", "content": _FEWSHOT_IA_INTENT},
        {
            "role": "assistant",
            "content": json.dumps(_FEWSHOT_GATE_INSTANT, ensure_ascii=False),
        },
        {"role": "user", "content": intent},
    ]


def messages_for_create_path(
    intent: str,
    *,
    path_start: PathStartSurface | dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Phase 2: PathState-only schema after gate chose kind=path."""
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": _CREATE_PATH_SYSTEM},
        {"role": "user", "content": _FEWSHOT_PATH_INTENT},
        {
            "role": "assistant",
            "content": json.dumps(_FEWSHOT_PATH["path"], ensure_ascii=False),
        },
        {"role": "user", "content": _FEWSHOT_FITNESS_INTENT},
        {
            "role": "assistant",
            "content": json.dumps(_FEWSHOT_FITNESS["path"], ensure_ascii=False),
        },
    ]
    if path_start is not None:
        start_payload = (
            path_start.model_dump(mode="json")
            if isinstance(path_start, PathStartSurface)
            else path_start
        )
        messages.append(
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "intent": intent,
                        "path_start": start_payload,
                        "instruction": (
                            "Build the full Path for this intent. Align with "
                            "path_start the user already saw."
                        ),
                    },
                    ensure_ascii=False,
                ),
            }
        )
    else:
        messages.append({"role": "user", "content": intent})
    return messages


def messages_for_create(intent: str) -> list[dict[str, Any]]:
    """Backward-compat alias — prefer messages_for_create_gate."""
    return messages_for_create_gate(intent)


def messages_for_materialize_plugins(
    *,
    current_state: dict[str, Any],
    hinted_actions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Phase 3: fill plugin payloads for actions that have plugin_hints."""
    return [
        {"role": "system", "content": _MATERIALIZE_SYSTEM},
        {
            "role": "user",
            "content": json.dumps(
                {
                    "hinted_actions": [
                        {
                            "action_id": "cook",
                            "title": "Приготовить карбонару",
                            "plugin_hints": ["timeline"],
                            "detail": (
                                "Prep/mise already done as checklist. "
                                "Timeline = heat → pasta water → emulsify → plate. "
                                "No cut/chop markers."
                            ),
                        }
                    ],
                    "domain": "cooking",
                },
                ensure_ascii=False,
            ),
        },
        {
            "role": "assistant",
            "content": json.dumps(
                _FEWSHOT_MATERIALIZE_CARBONARA, ensure_ascii=False
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "hinted_actions": [
                        {
                            "action_id": "d0",
                            "title": "Силовая сессия",
                            "plugin_hints": ["stepper"],
                            "detail": "Замер → отдых → подходы",
                        },
                        {
                            "action_id": "d2",
                            "title": "Силовая сессия",
                            "plugin_hints": ["stepper"],
                            "detail": "Замер и подходы",
                        },
                    ],
                    "domain": "fitness",
                },
                ensure_ascii=False,
            ),
        },
        {
            "role": "assistant",
            "content": json.dumps(
                _FEWSHOT_MATERIALIZE_FITNESS, ensure_ascii=False
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "outcome": current_state.get("outcome"),
                    "domain": current_state.get("domain"),
                    "hinted_actions": hinted_actions,
                },
                ensure_ascii=False,
            ),
        },
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
    intent: str | None = None,
) -> list[dict[str, Any]]:
    payload: dict[str, Any] = {
        "current_state": current_state,
        "reason": reason,
        "project_status": project_status,
    }
    if intent:
        payload["intent"] = intent
    return [
        {"role": "system", "content": _REPAIR_SYSTEM},
        {
            "role": "user",
            "content": json.dumps(payload, ensure_ascii=False),
        },
    ]


def messages_for_next_cycle(
    *,
    prior_state: dict[str, Any],
    cycle_result: dict[str, Any],
    answers: list[dict[str, str]],
    comment: str | None,
    next_index: int,
    continue_kind: str,
) -> list[dict[str, Any]]:
    return [
        {"role": "system", "content": _NEXT_CYCLE_SYSTEM},
        {
            "role": "user",
            "content": json.dumps(
                {
                    "prior_state": prior_state,
                    "cycle_result": cycle_result,
                    "answers": answers,
                    "comment": comment,
                    "next_index": next_index,
                    "continue_kind": continue_kind,
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
            hints = action.get("plugin_hints")
            if not isinstance(hints, list):
                action["plugin_hints"] = []
            else:
                cleaned_hints: list[str] = []
                for hint in hints:
                    if isinstance(hint, str) and hint.strip():
                        cleaned_hints.append(hint.strip())
                action["plugin_hints"] = cleaned_hints
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
            # Path #2 wire omits plugins — default empty. Legacy / #3 merge may
            # still include them; normalize sentinels when present.
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
            timeline = action.get("timeline")
            if isinstance(timeline, dict):
                timeline = dict(timeline)
                duration = timeline.get("duration_sec", -1)
                markers = timeline.get("markers") or []
                if not isinstance(markers, list):
                    markers = []
                normalized_markers: list[Any] = []
                for marker in markers:
                    if not isinstance(marker, dict):
                        continue
                    marker = dict(marker)
                    # Accept legacy at_sec from older drafts / API dumps.
                    if "sec" not in marker and "at_sec" in marker:
                        marker["sec"] = marker.pop("at_sec")
                    normalized_markers.append(marker)
                timeline["markers"] = normalized_markers
                if duration is None or duration == -1 or (
                    isinstance(duration, int) and duration < 1
                ):
                    action["timeline"] = None
                else:
                    action["timeline"] = timeline
            interval = action.get("interval_plan")
            if isinstance(interval, dict):
                interval = dict(interval)
                segments = interval.get("segments") or []
                if not isinstance(segments, list):
                    segments = []
                normalized_segments: list[Any] = []
                for segment in segments:
                    if not isinstance(segment, dict):
                        continue
                    segment = dict(segment)
                    if "sec" not in segment and "duration_sec" in segment:
                        segment["sec"] = segment.pop("duration_sec")
                    normalized_segments.append(segment)
                if not normalized_segments:
                    action["interval_plan"] = None
                else:
                    interval["segments"] = normalized_segments
                    action["interval_plan"] = interval
            action["stepper"] = _normalize_stepper_dict(action.get("stepper"))
            normalized_actions.append(action)
        out["actions"] = normalized_actions

    return out


def _normalize_stepper_dict(stepper: Any) -> Any:
    """Clear empty stepper stubs; normalize beat counter/duration sentinels."""
    if not isinstance(stepper, dict):
        return stepper
    stepper = dict(stepper)
    beats = stepper.get("beats") or []
    if not isinstance(beats, list) or not beats:
        return None
    normalized_beats: list[Any] = []
    for beat in beats:
        if not isinstance(beat, dict):
            continue
        beat = dict(beat)
        beat["id"] = _empty_to_none(beat.get("id"))
        normalized_beats.append(beat)
    if not normalized_beats:
        return None
    stepper["beats"] = normalize_stepper_beats(normalized_beats)
    return stepper


def normalize_plugin_payload_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Normalize one ActionPluginPayload wire dict (sentinels → None)."""
    out = dict(data)
    timers = out.get("timers")
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
        out["timers"] = normalized_timers
    elif timers is None:
        out["timers"] = []
    counter = out.get("counter")
    if isinstance(counter, dict):
        counter = dict(counter)
        counter["label"] = _empty_to_none(counter.get("label"))
        target = counter.get("target", -1)
        if target is None or target == -1:
            out["counter"] = None
        else:
            out["counter"] = counter
    timeline = out.get("timeline")
    if isinstance(timeline, dict):
        timeline = dict(timeline)
        duration = timeline.get("duration_sec", -1)
        markers = timeline.get("markers") or []
        if not isinstance(markers, list):
            markers = []
        normalized_markers: list[Any] = []
        for marker in markers:
            if not isinstance(marker, dict):
                continue
            marker = dict(marker)
            if "sec" not in marker and "at_sec" in marker:
                marker["sec"] = marker.pop("at_sec")
            normalized_markers.append(marker)
        timeline["markers"] = normalized_markers
        if duration is None or duration == -1 or (
            isinstance(duration, int) and duration < 1
        ):
            out["timeline"] = None
        else:
            out["timeline"] = timeline
    interval = out.get("interval_plan")
    if isinstance(interval, dict):
        interval = dict(interval)
        segments = interval.get("segments") or []
        if not isinstance(segments, list):
            segments = []
        normalized_segments: list[Any] = []
        for segment in segments:
            if not isinstance(segment, dict):
                continue
            segment = dict(segment)
            if "sec" not in segment and "duration_sec" in segment:
                segment["sec"] = segment.pop("duration_sec")
            normalized_segments.append(segment)
        if not normalized_segments:
            out["interval_plan"] = None
        else:
            interval["segments"] = normalized_segments
            out["interval_plan"] = interval
    out["stepper"] = _normalize_stepper_dict(out.get("stepper"))
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
        # Dropped from Anthropic Path wire schema (grammar size); default empty.
        data.setdefault("resources", [])
        data.setdefault("milestones", [])
    return PathState.model_validate(data)


def parse_plugins_materialize(raw_response: Any) -> ActionPluginsMaterialize:
    if isinstance(raw_response, ActionPluginsMaterialize):
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
        return ActionPluginsMaterialize.model_validate(data)
    out = dict(data)
    actions = out.get("actions")
    if isinstance(actions, list):
        normalized: list[Any] = []
        for item in actions:
            if isinstance(item, dict):
                normalized.append(normalize_plugin_payload_dict(item))
            else:
                normalized.append(item)
        out["actions"] = normalized
    return ActionPluginsMaterialize.model_validate(out)


def _is_empty_path_start_stub(payload: Any) -> bool:
    if payload is None:
        return True
    if not isinstance(payload, dict):
        return False
    paraphrase = payload.get("paraphrase")
    title = payload.get("title")
    summary = payload.get("summary")
    questions = payload.get("questions") or []
    return (
        (not paraphrase)
        and (not title)
        and (not summary)
        and len(questions) == 0
    )


def parse_create_gate(raw_response: Any) -> CreateGateResponse:
    """Parse phase-1 gate (kind + optional instant_answer / path_start)."""
    if isinstance(raw_response, CreateGateResponse):
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
        return CreateGateResponse.model_validate(data)

    out = dict(data)
    kind = out.get("kind")
    ia = out.get("instant_answer")
    start = out.get("path_start")
    if kind == "path":
        if _is_empty_path_start_stub(start):
            raise ValueError("path_start is required when kind=path")
        path_start = PathStartSurface.model_validate(start)
        return CreateGateResponse(
            kind="path",
            instant_answer=None,
            path_start=path_start,
        )
    if kind == "instant_answer":
        if _is_empty_instant_stub(ia):
            raise ValueError(
                "instant_answer is required when kind=instant_answer"
            )
        payload = InstantAnswerPayload.model_validate(ia)
        return CreateGateResponse(
            kind="instant_answer",
            instant_answer=payload,
            path_start=None,
        )
    raise ValueError(f"Unknown kind: {kind!r}")


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
            out["path"].setdefault("resources", [])
            out["path"].setdefault("milestones", [])
    elif kind == "instant_answer":
        out["path"] = None
    else:
        # Defensive: still normalize if a path object is present.
        path = out.get("path")
        if isinstance(path, dict) and not _is_empty_path_stub(path):
            out["path"] = normalize_path_wire_dict(path)
            out["path"].setdefault("resources", [])
            out["path"].setdefault("milestones", [])
        if _is_empty_instant_stub(out.get("instant_answer")):
            out["instant_answer"] = None
        if _is_empty_path_stub(out.get("path")):
            out["path"] = None

    return CreateLlmResponse.model_validate(out)
