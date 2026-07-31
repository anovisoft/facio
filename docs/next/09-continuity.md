# 09 — Continuity (не потерять после суммаризации чата)

Рабочая память на стыке сессий. Спека продукта — в `01`–`08`; здесь — **что уже сделано в коде**, **жёсткие решения**, **открытый хвост**.

Обновлять при закрытии среза / важном инциденте.

---

## Процесс

- Продукт и план — markdown в `docs/next`.
- Реализация — поэтапно субагентам (Срезы 1→5 из [08](./08-impl-plan.md)); куратор не делает весь next одним заходом.
- После среза: dogfood → одобрение → следующий срез.
- Внешний юзер-тест текущего билда — **рано** (см. [07](./07-testing-stance.md)); сначала dogfood эталонов.

---

## Статус срезов (на момент записи)

| Срез | Содержание | Статус |
|------|------------|--------|
| 1 | Narrative (title/summary) + batch clarify + comment | **одобрен** (+ UX: custom answer, keyboard, header, back button) |
| 2 | Cycle + days/kind + Home «день N» + Path day map | **одобрен** (+ hierarchy PathList, rest nesting) |
| 3 | TimerStack + Counter | **dogfood ок** |
| 3′ | Progressive create + clock UX + схлоп Accept | **в коде:** #2 Path+hints / #3 plugins after start |

| 4 | Repair на живом плане | не начат |
| 5 | Next cycle CTA | не начат |

Миграции backend (по порядку): `005` narrative → `006` cycle/schedule → `007` action plugins → `008` timeline/interval.

---

## Продуктовые решения после dogfood Среза 3 (зафиксировано)

### A. Draft → Accept → live — цикл устарел

Accept дублирует draft: карта уже полная на create (H1 выполнена). Hard commit имел смысл, когда Accept = «впервые показали план».

**Направление:** один **живой план**, всегда правится. Под капотом — явные операции (refine / repair / next cycle / comment), не свободный чат. Снаружи — план + жесты, не лента сообщений.

- Accept схлопывается в лёгкий «начать сегодня» / контракт на том же экране, либо исчезает как отдельный дубль PathList.
- Repair — не «режим после Accept», а тот же edit-loop на живом плане (срыв дня = мутация state).
- Не возвращать chat-home; принцип «Plan as Runtime Artifact» сильнее, не слабее.

Следствие для Среза 4: реализовать Repair уже как универсальную мутацию живого плана, не как заплатку на мёртвый draft-цикл.

### B. Progressive create — 3 фазы (зафиксировано после hang dogfood)

Hang: slim кадр пришёл, «Собираю полный план…» навсегда. Причина: phase-2 Path+**все plugins** → Anthropic **400 grammar too large**. Failed llm_call откатывался вместе с job → в `llm_calls` виден только успешный gate.

**Канон create (path):**

| # | Когда | Что | Schema |
|---|--------|-----|--------|
| **1** | сразу | Gate + start surface (paraphrase/title/summary/questions/outline) | маленькая (уже есть) |
| **2** | фон после #1 | Полный Path **без** plugins; на action — короткие **plugin hints** | Path без timers/timeline/interval/counter objects |
| **3** | после «Начать сегодня» | Materialize plugins (timeline/interval/timers/counter) по hints | крошечная, можно позже дробить на несколько #3 с разными форматами |

Instant = только #1.

**Hints на плане (не live UI):** например `plugin_hints: ["timeline"]` / `["counter","interval"]` — badge «будет таймлайн», не полный progress bar.

**Не делаем:** отдельную кнопку «Загрузить плагины» как главный жест (техдолг). Retry — только если #3 упал.

**Позже:** если plugins разрастутся — несколько запросов #3 с разными response formats (clock отдельно от counter и т.д.).

Планирование = смысл + дни + шаги (+ анонс tools). Использование = исполняемые plugins. «Начать сегодня» = граница preview→live (+ kick #3).

### C. Семейство clock-плагинов (не только плоский TimerStack)

Dogfood карбонары: плоский `timers[]` есть, но юзабельность слабая — нужна **ось времени сессии** (progress bar + маркеры). При этом простые таймеры **не выкидываем**.

| Shape | Когда | Пример |
|-------|--------|--------|
| **Timer / TimerStack** | Отдельный отсчёт, ручной Start | «10 мин на расстойку» |
| **Timeline** | Одна ось + markers `{at_sec, title, signal}` + progress | Карбонара: 0 → 2' помешать → 5' → 8' alert |
| **Interval plan** | Последовательность сегментов + **pause/resume** | 40s упр. → 20s отдых → 40s упр. |

Общий runtime-движок часов (elapsed, pause, complete segment/marker).  
**На wire create #2 plugins не тащить** — только hints; полные shapes в #3 после start (см. B).

Slice 3 закрыл «plugins есть в модели/UI». Slice 3′: progressive + clock UI; grammar → split #2/#3.

---

## Anthropic structured outputs (критично)

### Симптом

```text
400: The compiled grammar is too large…
```

Лимит у **feature constrained decoding / json_schema**, не у «толщины» модели. **Sonnet не поможет** — тот же лимит, что у Haiku.

### Что уже сделали

1. **Slim wire schema** (`anthropic_llm._anthropic_json_schema` + normalize в `path_llm`):
   - strip `description` с wire (guidance в промптах)
   - collapse `anyOf`/`null` → non-null + sentinels (`""`, `-1`, stub objects)
   - после parse: sentinels → `None` / нормальный PathState

2. **После Slice 3 снова 400** — dual-branch create (`path` + `instant_answer` в одной schema) + plugins не влезали.

3. **Split create gate** (текущее решение):
   - Фаза 1: `CREATE_GATE_SCHEMA` (~1380 chars wire) → `{kind, instant_answer, path_start}`
     - `path_start`: paraphrase / title / summary / questions / outline_days (titles only)
   - Если `instant_answer` → готово (1 LLM call)
   - Если `path` → сразу persist project + return `path_ready=false`; Фаза 2 в BackgroundTasks: `PATH_RESPONSE_SCHEMA` only
   - Legacy `CREATE_RESPONSE_SCHEMA` **не** шлётся в Anthropic (только тесты / сборка)
- Path-create → **2** строки в `llm_calls` (gate + path); клиент поллит GET до `path_ready`
- `resources` / `milestones` убраны с Anthropic wire (сервер → `[]`); в модели API поля живы

4. **Решение B (Slice 3′ fix):** Path wire **без** plugin objects + `plugin_hints[]`; полный clock/counter — call **#3** после Start:
   - `PATH_RESPONSE_SCHEMA` Anthropic wire ≈ **2996 chars** (было ~4383 с plugins → grammar 400; цель ≤~3k)
   - `PLUGINS_MATERIALIZE_SCHEMA` ≈ **1853 chars** (action_id → timers/timeline/interval_plan/counter)
   - Gate ≈ **1380 chars** (без изменений)
   - Failed #2/#3: `llm_calls` + `path_error` turn **коммитятся** (не rollback audit)
   - UI: Draft крутит spinner только пока нет `path_error`; Home поллит `plugins_ready`

### Запасной ход (ещё не включали)

**Strategy C:** JSON без schema + `PathState.model_validate` + retry — если Path wire снова упрётся в grammar (Slice 4/5 с новыми nested полями).

### Не делать

- Лечить 400 сменой Haiku→Sonnet
- Снова требовать full PathState + InstantAnswer в одном structured call

---

## Day `kind` — продуктовая договорённость

`kind` = **роль дня для runtime**, не тема жизни.

| Ок | Не ок |
|----|--------|
| `train` \| `rest` \| `cook_session` \| `other` | `подработать`, `учить_испанский`, отдельный kind на каждый intent |

Новые kind — только если появляется **другое поведение** UI/правил (не другое слово в title). Домен/сюжет — в `domain`, `title`/`summary` дня и шагах. `other` — запасной люк.

---

## UI иерархия Path (зафиксировано в коде)

Канон при наличии `days[]`:

```text
title + summary плана
План цикла · N дней     ← тихий meta
▸ День N · kind         ← единственный сильный section header
    шаги (нумерация внутри дня)
    groups: multi-day скрыты; single-day (карбонара) — тихие captions
```

- Не оборачивать **только rest** в отдельную большую карточку секции (был баг «день то сверху, то вложен») — убран; rest = muted title + left accent, тот же nesting что train.
- В `action.title` не писать «день N» (промпт); день через `day_offset` + UI.
- Draft/Accept: не дублировать «Черновик пути» / «Весь путь» как ещё один uppercase label над PathList.

---

## Plugins (Срез 3 / 3′ clock — что в коде сейчас)

На action:

- `timers[]`: id, title, duration_sec, signal (`nudge`|`alert`), parallel_group
- `counter`: label, target, current, step (wire stub `target:-1` → null)
- `timeline`: duration_sec + markers[] (`sec` on wire = absolute `at_sec`; API exposes `at_sec`). Stub `{duration_sec:-1, markers:[]}` → null
- `interval_plan`: segments[] (`sec` on wire = segment `duration_sec`; API exposes `duration_sec`). Stub `{segments:[]}` → null
- checklist как было

Wire slim trick: shared `PathClockBeat` `{sec, title, signal}` for timeline markers and interval segments — used on **#3** materialize wire only (not on Path #2).

UI: draft — plugin **hint chips** when hints present and payloads empty; Home/Path live — Start таймеров, timeline progress + pause, interval play/pause, ± каунтера after #3.  
Сигналы: nudge = короткая вибро; alert = сильнее + notification.  
API: `POST .../counter`, `POST .../timers/{id}/complete`. Timeline/interval runtime — client-side (v1), plan data persisted on actions JSONB (`008_clock_plugins`). ProjectDetail: `path_ready`, `path_error`, `plugins_ready`.

Эталоны: карбонара cook → **hint timeline** (+ optional timers) → #3 timeline; отжимания day0 → **hints interval+counter** → #3 payloads; other train → counter hints.

Миграции: `005` narrative → `006` cycle/schedule → `007` action plugins → `008` timeline/interval_plan.

---

## Известный backlog (не блокер среза, не забыть)

| Тема | Заметка |
|------|---------|
| Progressive create | **done (Срез 3′)**: #1 gate → #2 Path+hints → #3 plugins after Start; Accept схлопнут в «Начать сегодня» |
| Always-editable план | Accept-дубль PathList убран; Repair = общий edit (решение A) — рамка для Среза 4+ |
| Timeline / Interval plugins | **в коде** — #2 hints; #3 materialize; live UI after Start |
| Clarify options отжиманий | Не мешать ось «сколько раз» и «с колен/стены» в одном ряду чипов |
| Home перегружен | Много labels; declutter вместе с контролами / always-editable |
| 8 недель vs cycle 7 дней | Narrative программы vs текущий cycle — явно на next cycle (Срез 5) |
| Strip «день N» из старых title | Промпт чинит новые create; старые draft могут содержать |
| Latency path-фазы | Полный Path всё ещё ~десятки секунд — ок на фоне, если slim уже на экране; резать tokens_out / few-shots |
| resources/milestones | Не в structured wire — вернуть иначе, если понадобятся |
| Strategy C | Fallback без structured outputs, если снова grammar 400 |
| Split #3 formats | Позже: несколько #3 с разными response formats (clock vs counter) |

---

## Следующий шаг

Срез 3′: #2 Path+hints / #3 plugins after start **в коде** (wire Path ≈2996).  
**Dogfood** на эталонах → одобрение 3′ → Срез 4.

### Dogfood после фикса

1. Restart backend + миграции при необходимости
2. Create карбонара → slim → план с timeline hint (**не hang**) → «Начать сегодня» → #3 plugins → timeline live
3. Отжимания → hints → после start interval/counter
4. Failed llm_calls остаются в audit; UI не крутит спиннер вечно (`path_error`)
5. Instant `2^100` ок; нет Accept-дубля

Потом → одобрение 3′ → Срез 4.

---

## Эталоны качества

См. [06](./06-reference-scenarios.md): карбонара + путь к ~30 отжиманиям. Остальной intent — best-effort.

---

## Связанные файлы (ориентир)

| Область | Где |
|---------|-----|
| Gate / create split | `app/schemas/create_response.py`, `app/services/path.py` (`create_from_intent`) |
| Path #2 / plugins #3 | `path_state.PATH_RESPONSE_SCHEMA`, `PLUGINS_MATERIALIZE_SCHEMA`; `complete_materialize_plugins_job` |
| Промпты / sentinels / normalize | `app/services/path_llm.py` |
| Wire transform Anthropic | `app/providers/anthropic_llm.py` |
| PathState + plugins + hints | `app/schemas/path_state.py` |
| Path UI hierarchy + hint chips | `apps/mobapp-rn/src/shared/ui/PathList.tsx` |
| Home plugins + plugins_ready poll | `ProjectHomeScreen.tsx` + plugin components |
| План срезов | [08](./08-impl-plan.md) |
