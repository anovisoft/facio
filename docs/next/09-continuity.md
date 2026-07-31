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
| 3′ | Progressive create + clock UX (timeline/interval) + схлоп Accept | **код готов** (A+B); ждёт dogfood |
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

### B. Progressive create — slim первый кадр

~20с до первого отклика убивает ощущение. Path = gate + полный PathState слишком поздно показывает пользу.

**Направление create:**

1. **Slim call (фаза 1)** — выбирает путь **и** даёт минимальную поверхность:
   - `instant_answer` → ответ сразу
   - `path` → paraphrase / title / summary-черновик + batch questions (+ опционально грубый outline дней, **без** plugins / полного PathState)
2. Пользователь сразу видит «ведём к…» и может отвечать на уточнения.
3. **Полный Path + plugins** — фаза 2 на фоне; UI мягко подменяется, когда готов.

Не путать с «прятать маршрут до Accept»: скрываем только **полноту исполняемого слоя**, не первый полезный сигнал.

Slim-схема обязана остаться маленькой (grammar). Не тащить plugins/`days[]` целиком в фазу 1.

Текущий gate (`kind` + instant only) — промежуточный шаг; расширить до «start surface».

### C. Семейство clock-плагинов (не только плоский TimerStack)

Dogfood карбонары: плоский `timers[]` есть, но юзабельность слабая — нужна **ось времени сессии** (progress bar + маркеры). При этом простые таймеры **не выкидываем**.

| Shape | Когда | Пример |
|-------|--------|--------|
| **Timer / TimerStack** | Отдельный отсчёт, ручной Start | «10 мин на расстойку» |
| **Timeline** | Одна ось + markers `{at_sec, title, signal}` + progress | Карбонара: 0 → 2' помешать → 5' → 8' alert |
| **Interval plan** | Последовательность сегментов + **pause/resume** | 40s упр. → 20s отдых → 40s упр. |

Общий runtime-движок часов (elapsed, pause, complete segment/marker); LLM выбирает shape на шаге. Схему **не раздувать** тремя монстрами — заменить/дополнить peer-list timeline/interval там, где ось нужна.

Slice 3 закрыл «plugins есть». Timeline / interval — следующий слой плагина (не блокер Repair, но must до объявления runtime wedge «готово»).

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
- Path wire после clock family (~4383 chars) — ещё под потолком 4500; Strategy C если снова 400

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

Wire slim trick: shared `PathClockBeat` `{sec, title, signal}` for timeline markers and interval segments (Path wire ~4383 chars, under 4500 ceiling).

UI: draft/accept — preview disabled; Home/Path live — Start таймеров, timeline progress + pause, interval play/pause, ± каунтера.  
Сигналы: nudge = короткая вибро; alert = сильнее + notification.  
API: `POST .../counter`, `POST .../timers/{id}/complete`. Timeline/interval runtime — client-side (v1), plan data persisted on actions JSONB (`008_clock_plugins`).

Эталоны: карбонара cook → **timeline** (+ optional simple timer for guanciale); отжимания day0 → **interval_plan** circuit + counter; other train → counters.

Миграции: `005` narrative → `006` cycle/schedule → `007` action plugins → `008` timeline/interval_plan.

---

## Известный backlog (не блокер среза, не забыть)

| Тема | Заметка |
|------|---------|
| Progressive create | **done (часть A Среза 3′)**: slim `path_start` + background Path; Accept схлопнут в «Начать сегодня» на DraftStudio |
| Always-editable план | Accept-дубль PathList убран; Repair = общий edit (решение A) — рамка для Среза 4+ |
| Timeline / Interval plugins | **в коде (Срез 3′ B)** — карбонара timeline; fitness day0 interval+pause; TimerStack сохранён |
| Clarify options отжиманий | Не мешать ось «сколько раз» и «с колен/стены» в одном ряду чипов |
| Home перегружен | Много labels; declutter вместе с контролами / always-editable |
| 8 недель vs cycle 7 дней | Narrative программы vs текущий cycle — явно на next cycle (Срез 5) |
| Strip «день N» из старых title | Промпт чинит новые create; старые draft могут содержать |
| Latency path-фазы | Полный Path всё ещё ~десятки секунд — ок на фоне, если slim уже на экране; резать tokens_out / few-shots |
| resources/milestones | Не в structured wire — вернуть иначе, если понадобятся |
| Strategy C | Fallback без structured outputs, если снова grammar 400 |

---

## Следующий шаг

Срез 3′ **A+B в коде**. Dogfood → одобрение → Срез 4.

### Dogfood 3′

1. Restart backend + `alembic upgrade head` (через `008`)
2. Create карбонара → slim кадр (title/summary/questions) быстро → «Собираю полный план…» → PathList с **timeline**; «Начать сегодня» → Home, Start timeline + pause; guanciale timer ещё работает
3. Create отжимания → day0 **interval** + pause; counters на других днях
4. Instant `2^100` → один LLM call
5. Нет экрана Accept с дублем PathList
6. Нет grammar 400; path-create: gate + background path (poll `path_ready`)

Риск: phase-2 fail оставляет `path_ready=false` без retry UI.

---

## Эталоны качества

См. [06](./06-reference-scenarios.md): карбонара + путь к ~30 отжиманиям. Остальной intent — best-effort.

---

## Связанные файлы (ориентир)

| Область | Где |
|---------|-----|
| Gate / create split | `app/schemas/create_response.py`, `app/services/path.py` (`create_from_intent`) |
| Промпты / sentinels / normalize | `app/services/path_llm.py` |
| Wire transform Anthropic | `app/providers/anthropic_llm.py` |
| PathState + plugins + wire drop resources | `app/schemas/path_state.py` |
| Path UI hierarchy | `apps/mobapp-rn/src/shared/ui/PathList.tsx` |
| Home plugins | `ProjectHomeScreen.tsx` + plugin components |
| План срезов | [08](./08-impl-plan.md) |
