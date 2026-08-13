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
| 3′ | Progressive create + clock UX + схлоп Accept + Draft UX D | **одобрен** (polish later) |
| 4 | Repair + **физический день** на живом плане | **принят** |
| 4′ | Session Stage + Stepper + бургер→план | **принят** |
| 5 | Next cycle CTA | **принят** (карбонара dogfood; fitness N+1 отложен) |

Миграции backend (по порядку): `005` narrative → `006` cycle/schedule → `007` action plugins → `008` timeline/interval → `009` physical day → `010` stepper JSONB → **`011` cycle_result + cycles_history**.

---

## Продуктовые решения после dogfood Среза 3 (зафиксировано)

### A. Draft → Accept → live — цикл устарел

Accept дублирует draft: карта уже полная на create (H1 выполнена). Hard commit имел смысл, когда Accept = «впервые показали план».

**Направление:** один **живой план**, всегда правится. Под капотом — явные операции (refine / repair / next cycle / comment), не свободный чат. Снаружи — план + жесты, не лента сообщений.

- Accept схлопывается в лёгкий «начать сегодня» / контракт на том же экране, либо исчезает как отдельный дубль PathList.
- Repair — не «режим после Accept», а тот же edit-loop на живом плане (срыв дня = мутация state).
- Не возвращать chat-home; принцип «Plan as Runtime Artifact» сильнее, не слабее.

Следствие для Среза 4: (1) **физический день** — calendar unlock от якоря commit; (2) Repair как универсальная мутация живого плана на фоне unlock, не заплатка на мёртвый draft-цикл.

### E. Физический день (зафиксировано — must в Срезе 4)

Dogfood: день 1 закрыт → сразу день 2. Программный `day_index` есть, **wall-clock нет**.

**Канон:**
- `cycle_anchor_date` от commit (`first_step_when` today/tomorrow сдвигает D0)
- `unlocked = -1` до anchor; иначе `min(local_today − anchor, horizon−1)` — локальная дата с клиента
- Execute только `day_index ≤ unlocked` (catch-up на незакрытом прошлом ок)
- **Будущие дни смотреть можно** (карта / весь план / peek); complete/skip/plugins — нет
- horizon=1 (карбонара) + commit today — без регресса
- Repair intents: shift / lighten / rest + summary banner

Детали: [04 §4](./04-model.md), [08 Срез 4](./08-impl-plan.md).

### F. Session Stage + Stepper + бургер (зафиксировано — **в коде**, Срез 4′)

Dogfood: Home = буклет; силовая = checklist подходов + один counter; max+volume двумя action.

**Канон (реализовано):**
- Home: **Session Stage** (~2/3) = timeline | stepper beat | interval — герой экрана; support-текст ниже
- **Бургер справа сверху** → Весь план (`Path`); дубль CTA «Весь план» в теле убран
- Wire name: **`stepper`** (не `set_plan`); beats `measure | work | rest`
- Hint `#2`: `"stepper"`; полные beats в `#3` внутри `PLUGINS_MATERIALIZE_SCHEMA` (~2506 chars wire, бюджет теста `<2800`)
- Один train-день = один session action; запрет checklist-подходов в промптах/few-shot
- Compact sticky при скролле — **не** в этом срезе (should-have later)

Детали: [04 §5](./04-model.md), [05 Session Stage](./05-ux-flows.md), [08 Срез 4′](./08-impl-plan.md).

### B. Progressive create — 3 фазы (зафиксировано после hang dogfood)

Hang: slim кадр пришёл, «Собираю полный план…» навсегда. Причина: phase-2 Path+**все plugins** → Anthropic **400 grammar too large**. Failed llm_call откатывался вместе с job → в `llm_calls` виден только успешный gate.

**Канон create (path):**

| # | Когда | Что | Schema |
|---|--------|-----|--------|
| **1** | сразу | Gate + start surface (paraphrase/title/summary/questions/outline) | маленькая (уже есть) |
| **2** | фон после #1 | Полный Path **без** plugins; на action — короткие **plugin hints** | Path без timers/timeline/interval/counter objects |
| **3** | после «Начать сегодня» | Materialize plugins (timeline/interval/timers/counter/**stepper**) по hints | крошечная; stepper можно отдельным #3 format |

Instant = только #1.

**Hints на плане (не live UI):** например `plugin_hints: ["timeline"]` / `["counter","interval"]` — badge «будет таймлайн», не полный progress bar.

**Не делаем:** отдельную кнопку «Загрузить плагины» как главный жест (техдолг). Retry — только если #3 упал.

**Позже:** если plugins разрастутся — несколько запросов #3 с разными response formats (clock отдельно от counter и т.д.).

Планирование = смысл + дни + шаги (+ анонс tools). Использование = исполняемые plugins.  
CTA после commit: **«Сохранить и приступить»** (→ Home + #3) / вторичная **«Сохранить»** (→ Projects). Сегодня/завтра switcher **убран**.

### C. Семейство clock-плагинов (не только плоский TimerStack)

Dogfood карбонары: плоский `timers[]` есть, но юзабельность слабая — нужна **ось времени сессии** (progress bar + маркеры). При этом простые таймеры **не выкидываем**.

| Shape | Когда | Пример |
|-------|--------|--------|
| **Timer / TimerStack** | Отдельный отсчёт, ручной Start | «10 мин на расстойку» |
| **Timeline** | Одна ось + markers `{at_sec, title, signal}` + progress | Карбонара: 0 → 2' помешать → 5' → 8' alert |
| **Interval plan** | Последовательность сегментов + **pause/resume** | 40s упр. → 20s отдых → 40s упр. |

Общий runtime-движок часов (elapsed, pause, complete segment/marker).  
**На wire create #2 plugins не тащить** — только hints; полные shapes в #3 после start (см. B).

**Правило XOR:** на одном action не ставить real **timeline и timers вместе** — timeline владеет cook-сессией; timers только для изолированного ожидания без оси. Промпт + `merge_plugin_payloads` (если timeline.duration≥1 → timers=[]).

Slice 3 закрыл «plugins есть в модели/UI». Slice 3′: progressive + clock UI; grammar → split #2/#3.

### D. Draft studio UX (зафиксировано — **в коде**, ждёт dogfood)

Dogfood после #2/#3 + схлоп Accept выявил:

1. Пока отвечаешь на вопросы, приезжает полный PathList → **кнопка «Обновить путь» уезжает вниз** (палец промахивается).
2. После refine часто `questions=[]` → блок clarify (включая comment) **пропадает**, а refine при 0 вопросов требует comment → **тупик**.
3. Раньше: ответы сбрасывались при bump `current_version` когда доезжал path — **пофикшено** (сброс только при смене набора question id).
4. Порядок «полный план до вопросов» ломал логику; «полный план после вопросов» чинит смысл, но усиливает (1).

**Выбранный комбо (одобрено и реализовано):**

```text
title + summary
компактный OUTLINE (дни)   ← «план есть», не толкает CTA
вопросы (chips) — если есть
«Ещё важно» (comment) — ВСЕГДА, даже при 0 вопросов
[ STICKY FOOTER ]
  Обновить путь | Назад(version)
  Сохранить и приступить   (primary)
  Сохранить                (secondary → Projects)
полный PathList — по «Смотреть весь план» / развернуть
```

**В коде (Draft UX D):**
- `SafeScreen` `footer` prop — sticky CTA вне ScrollView + KeyboardAvoidingView
- `PlanOutline` из `project.days` (gate уже пишет outline в days через `path_state_from_start`)
- PathList только при expand; comment всегда; `questionRoundKey` preserve
- i18n: `outlineLabel` / `viewFullPlan` / `hideFullPlan`

Мягкий хвост (не блокер): outline пока только дни, без 3–7 строк шагов — можно добить после dogfood, если не хватает.

См. также [05](./05-ux-flows.md) Draft studio.

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
   - `PATH_RESPONSE_SCHEMA` Anthropic wire ≈ **3007 chars** (hints include `stepper`; no plugin objects)
   - `PLUGINS_MATERIALIZE_SCHEMA` ≈ **2506 chars** (timers/timeline/interval/counter/**stepper**; test budget `<2800`)
   - Gate ≈ **1380 chars** (без изменений)
   - Failed #2/#3: `llm_calls` + `path_error` turn **коммитятся** (не rollback audit)
   - UI: Draft крутит spinner только пока нет `path_error`; Home блокирует loader пока нет `plugins_ready` / есть `plugins_error` + retry

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
- `stepper`: beats[] `{id, kind: measure|work|rest, title, counter?, duration_sec?, signal?}`. Stub `{beats:[]}` → null. Hint `"stepper"`.
- checklist как было

Wire slim trick: shared `PathClockBeat` `{sec, title, signal}` for timeline markers and interval segments — used on **#3** materialize wire only (not on Path #2).

UI: draft — plugin **hint chips** when hints present and payloads empty (incl. stepper); Home Session Stage — timeline / stepper / interval as hero; Path live after #3.  
Сигналы: nudge = короткая вибро; alert = сильнее + notification.  
API: `POST .../counter`, `POST .../stepper/beats/{id}/counter`, `POST .../timers/{id}/complete`. Timeline/interval/stepper rest runtime — client-side (v1). ProjectDetail: `path_ready`, `path_error`, `plugins_ready`, `plugins_error`.

Эталоны: карбонара cook → **hint timeline** → #3 timeline; отжимания train → **hint stepper** → #3 beats (measure/work/rest).

Миграции: `005` … `008` clock → `009` physical day → `010` stepper.

**Dogfood hotfix (stepper + plugins loader):** measure/work beats without a real counter are soft-filled (`target=1`) on PathState / #3 normalize so Home never bricks on pydantic dumps. `get_latest_state` soft-fails to ORM for reads. Home blocks on «Собираю инструменты…» until `plugins_ready`; `plugins_error` + `POST .../materialize-plugins` for retry.

---

## Известный backlog (не блокер среза, не забыть)

| Тема | Заметка |
|------|---------|
| Progressive / Draft UX | **#1→#2→#3** + layout D — **одобрен**; polish later |
| Always-editable план | Accept-дубль убран (Save/Start); Repair = общий edit — Срез 4 |
| Queued refine while path #2 loads | **в коде**: CTA жмётся при `!path_error` (не ждёт `path_ready`); жмёт → busy «Жду план, затем обновлю…» → поллит до `path_ready`/`path_error` → refine тем же answers/comment (`DraftStudioScreen.runRefine` + `waitForPathReady`) |
| Fitness long cycle + rest tail | **в коде**: `normalize_cycle_horizon` — trim hollow rest-tail + **hard truncate** fitness→7 / else→14 (лишние days+actions отбрасываются → следующий цикл); retry nudge; gate/prompt ≤7 outline |
| Timeline / Interval | #2 hints; #3 materialize; XOR timeline/timers на одном шаге |
| Clarify options отжиманий | Не мешать ось «сколько раз» и «с колен/стены» в одном ряду чипов |
| Home перегружен | → Срез 4′ Session Stage — **в коде**; compact sticky later |
| Stepper / set_plan | **в коде** как wire `stepper` (миграция `010`); soft-normalize measure/work counters |
| Invalid PathState brick Home | **в коде**: normalize + soft `get_latest_state` (no raw pydantic to UI) |
| Plugins loader lock | **в коде**: Home blocking loader + `plugins_error` / rematerialize retry |
| RN `DOMException` on commit start | **частично**: убрали `new DOMException` из Draft `waitForPathReady` → `abortError()`. Скрин может быть stale **или** второй источник: `abort()` на unmount рвёт `fetch` → `whatwg-fetch` делает `reject(new DOMException(...))`, а в Hermes global `DOMException` битый/нет. **Открыто:** polyfill DOMException в `index.ts` и/или не abort'ить inflight на успешном commit navigation; проверить после reload бандла |
| Session Stage dogfood | Home всё ещё может выглядеть «буклетом», если #3 не дал timeline/stepper или plugins soft-fail → ORM без stage |
| 8 недель vs cycle 7 дней | Narrative программы vs текущий cycle — явно на next cycle (Срез 5) |
| Strip «день N» из старых title | Промпт чинит новые create; старые draft могут содержать |
| Latency path-фазы | Полный Path всё ещё ~десятки секунд — ок на фоне, если slim уже на экране; резать tokens_out / few-shots |
| resources/milestones | Не в structured wire — вернуть иначе, если понадобятся |
| Strategy C | Fallback без structured outputs, если снова grammar 400 |
| Split #3 formats | Позже: несколько #3 с разными response formats (clock vs counter) |

---

## Инциденты RN (не потерять)

### DOMException after «Сохранить и приступить»

1. **Первый фикс (в коде):** `DraftStudioScreen.waitForPathReady` больше не использует `DOMException` — `abortError()` / `isAbortError()`. В `apps/mobapp-rn/src` строк `DOMException` нет.
2. **Dogfood 2026-08-01:** после reload бандла — **ок**, краш не воспроизвёлся. Polyfill `whatwg-fetch` пока не нужен; держать в уме если вернётся на abort inflight fetch.

### Stepper validation brick Home (пофикшено)

`stepper measure/work beats need a counter` → soft-fill + soft `get_latest_state`. См. блок Plugins выше.

---

## Процесс / предпочтения куратора (сессия)

- Реализацию делать **субагентом**; куратор — архитектура, docs, review DoD.
- Модель субагента по умолчанию: `cursor-grok-4.5-high` (см. `.cursor/rules/subagent-models.mdc`); дешёвое — `composer-2.5`.
- Перед summarize чата — обновлять этот файл.

---

## Приёмка этапа (2026-08-01)

Срезы **1–5** принимаем как готовый этап `docs/next`.

| Эталон | Статус |
|--------|--------|
| Карбонара (create → timeline stage → завершение → «Повторить») | dogfood ок |
| Отжимания / fitness 7 дней (physical day + repair + next cycle) | **не прогнан end-to-end** |

**Почему fitness отложен:** physical-day gate привязан к календарю — полный прогон цикла = ждать ~неделю или манипулировать временем. Dev tools (fake `local_date` / advance anchor) — backlog ниже, не блокер приёмки этапа.

**Следствие:** этап закрыт по must-коду; полный dogfood-бар [07] и внешние юзеры — после time-travel или реального прогона недели.

---

## Следующий шаг

1. Этап принят — не открывать новый срез «по инерции»
2. По желанию: polish / backlog (Home stage, cook prep≠timeline, Repair comment+domain, **dev time travel**)
3. Fitness dogfood-бар + next cycle — когда есть time travel или неделя calendar

### Dogfood checklist (актуальный)

1. Create → ответы clarify **не сбрасываются** когда path #2 доезжает  
2. Queued refine: «Обновить» пока path грузится → ждёт → refine  
3. Outline + sticky CTA; «Ещё важно» при 0 questions  
4. Fitness cycle ≤7 дней; нет rest-хвоста 20–35  
5. Сохранить и приступить → **loader plugins** → Home stage (не буклет; DOMException ✓ после reload)  
6. Сохранить → список → открытие → loader если plugins ещё нет  
7. Бургер ☰ → весь план; locked days видны, execute нет  
8. Силовая: stepper beats (не checklist подходов + 1 counter)  
9. Карбонара: timeline stage; XOR timers; **prep вне оси** (нарезать ≠ marker) — см. backlog cook  
10. Physical day: закрыл день N ≠ execute N+1 сегодня  
11. Repair sheet shift/lighten/rest (**на fitness**; на cook — ожидаемо коряво, см. backlog)  
12. Нет grammar 400; `path_error` / `plugins_error` вместо вечного спиннера  
13. **Срез 5:** карбонара → итог + «Повторить» ✓; fitness «Следующий цикл» — отложен (нет time travel)  

### Срез 5 — что в коде

- `POST /projects/{id}/complete-cycle` — частичное/раннее завершение + `cycle_result`
- Авто-finish при закрытии всех actions → `cycle_status=completed` + `cycle_result`
- `POST /projects/{id}/next-cycle` — LLM `purpose=next_cycle`, archive в `cycles_history`, новый якорь, plugins #3
- Detail: `cycle_result`, `cycles_history`, `next_cycle_available`, `can_finish_cycle`, `continue_kind` (`next`|`repeat`)
- Home: summary + CTA; sheets finish / next+comment; i18n RU/EN
- Миграция `011_cycle_result_history.py`  

---

## Backlog (после приёмки этапа)

### Dev: time travel для dogfood

**Зачем:** physical day блокирует полный fitness/repair/next-cycle dogfood без ожидания недели.

**Направление (на выбор):**
- Debug/dev-only: override `local_date` на клиенте или `?local_date=` уже есть на API — UI picker / «+1 день»
- Или admin: сдвинуть `cycle_anchor_date` назад

Не для прод-пользователей.

### Repair: комментарий + domain intents

**Статус:** отложено. API уже: `POST /repair { intent?, reason? }`. UI: только 3 кнопки + hardcoded `t('home.repairReason')`.

1. **UI comment** — опциональное поле в `RepairSheet`; слать как `reason` (intent можно оставить или сделать optional если reason достаточный).
2. **Три intent не универсальны** — `shift / lighten / rest` ок для fitness multi-day; для **cook/instant** (карбонара) часто мимо:
   - `rest` бессмысленен для одноразовой сессии готовки
   - `lighten` («меньше подходов») не про рецепт
   - `shift` иногда ок («ужин завтра»), но срывы другие: нет ингредиента, мало времени, упростить блюдо, отменить вечер
3. **Направление:** domain-aware repair options (по `domain` / day kind) **или** primary = free reason + LLM, structured intents — secondary shortcuts. Детали UX — [05](./05-ux-flows.md) Repair future.

### Cook timeline: prep ≠ clock axis

**Статус:** **в коде / ждёт dogfood**.

Не два timeline / не табы на Home. Path:

1. action(s) **подготовка / mise** → `checklist` (нарезать, сыр, желтки…) — **без** timeline
2. action **сессия готовки** → один `timeline`, t=0 = старт жара / кипятка / критичной оси

**Запрещено:** mise («нарезать карбонад») как первый marker на timeline.  
Промпт #2/#3 + few-shot карбонара + factories/tests — выровнены.

### Home Session Stage polish

Stage ещё не ~2/3; support/буклет labels конкурируют; «Дальше» vs «Сделано» — иерархия CTA. После dogfood-бара / по желанию.

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
| PathState + plugins + hints + stepper | `app/schemas/path_state.py` (`normalize_stepper_beats`) |
| Horizon clamp / rest trim | `normalize_cycle_horizon` in `path_state.py` |
| Physical day | `app/services/schedule.py`, migration `009` |
| Stepper column | migration `010_action_stepper.py` |
| Next cycle | `app/services/cycle.py`, `path.py` finish/next; migration `011`; Home sheets |
| Path UI + hints | `apps/mobapp-rn/src/shared/ui/PathList.tsx` |
| Home Session Stage + plugins loader + burger | `ProjectHomeScreen.tsx`, `ActionPlugins.tsx` (`StepperPlayer`) |
| Draft queued refine + abortError | `DraftStudioScreen.tsx` |
| API client fetch+signal | `apps/mobapp-rn/src/api/client.ts` |
| План срезов | [08](./08-impl-plan.md) |
