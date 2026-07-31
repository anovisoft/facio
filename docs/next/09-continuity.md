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
| 3 | TimerStack + Counter | **dogfood ок** (plugins на create есть; grammar split gate ок). UX таймеров и create-latency — см. решения ниже |
| 4 | Repair | не начат — делать уже в рамке «живой план» (см. ниже) |
| 5 | Next cycle CTA | не начат |

Миграции backend (по порядку): `005` narrative → `006` cycle/schedule → `007` action plugins.

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
   - Фаза 1: `CREATE_GATE_SCHEMA` (~656 chars) → `{kind, instant_answer}`
   - Если `instant_answer` → готово (1 LLM call)
   - Если `path` → Фаза 2: `PATH_RESPONSE_SCHEMA` only (~3591 chars)
   - Legacy `CREATE_RESPONSE_SCHEMA` **не** шлётся в Anthropic (только тесты / сборка)
   - Path-create → **2** строки в `llm_calls`
   - `resources` / `milestones` убраны с Anthropic wire (сервер → `[]`); в модели API поля живы

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

## Plugins (Срез 3 — что в коде сейчас)

На action:

- `timers[]`: id, title, duration_sec, signal (`nudge`|`alert`), parallel_group
- `counter`: label, target, current, step (wire stub `target:-1` → null)
- checklist как было

UI: draft/accept — preview disabled; Home/Path live — Start таймеров, ± каунтера.  
Сигналы: nudge = короткая вибро; alert = сильнее + notification.  
API: `POST .../counter`, `POST .../timers/{id}/complete`.

Эталоны: карбонара → timers на cook; отжимания → counters на train (few-shots/промпты).

**Следующий слой (ещё не в коде):** Timeline + Interval plan — см. решение C выше; модель в [04](./04-model.md).

---

## Известный backlog (не блокер среза, не забыть)

| Тема | Заметка |
|------|---------|
| Progressive create | Расширить slim фазу 1 до start surface (решение B) — высокий ROI на ощущение |
| Always-editable план | Схлопнуть Draft/Accept; Repair = общий edit (решение A) — рамка для Среза 4+ |
| Timeline / Interval plugins | Карбонара progress bar; тренировки pause/playlist (решение C) |
| Clarify options отжиманий | Не мешать ось «сколько раз» и «с колен/стены» в одном ряду чипов |
| Home перегружен | Много labels; declutter вместе с контролами / always-editable |
| 8 недель vs cycle 7 дней | Narrative программы vs текущий cycle — явно на next cycle (Срез 5) |
| Strip «день N» из старых title | Промпт чинит новые create; старые draft могут содержать |
| Latency path-фазы | Полный Path всё ещё ~десятки секунд — ок на фоне, если slim уже на экране; резать tokens_out / few-shots |
| resources/milestones | Не в structured wire — вернуть иначе, если понадобятся |
| Strategy C | Fallback без structured outputs, если снова grammar 400 |

---

## Следующий шаг (после фиксации решений)

Порядок согласовать явно (не автоматом «сразу Срез 4»):

1. **Progressive create** (slim start surface) — бьёт 20с пустоты  
2. **Always-editable + Repair (Срез 4)** — в новой рамке, без дубля Accept  
3. **Timeline / Interval** — углубление clock-плагинов  

Можно 1 до или параллельно с подготовкой 4; 3 — не блокер Repair, но must до «runtime wedge готов».

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
