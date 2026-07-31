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
| 3 | TimerStack + Counter | **код есть**; grammar fix (split gate) есть — **ждёт dogfood** create карбонара/отжимания после restart backend |
| 4 | Repair | не начат |
| 5 | Next cycle CTA | не начат |

Миграции backend (по порядку): `005` narrative → `006` cycle/schedule → `007` action plugins. Нужен `alembic upgrade head`.

Срез 3 на iOS: после plugins нужен **rebuild** (`expo-notifications`, `expo-haptics`).

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

## Plugins (Срез 3)

На action:

- `timers[]`: id, title, duration_sec, signal (`nudge`|`alert`), parallel_group
- `counter`: label, target, current, step (wire stub `target:-1` → null)
- checklist как было

UI: draft/accept — preview disabled; Home/Path live — Start таймеров, ± каунтера.  
Сигналы: nudge = короткая вибро; alert = сильнее + notification.  
API: `POST .../counter`, `POST .../timers/{id}/complete`.

Эталоны: карбонара → timers на cook; отжимания → counters на train (few-shots/промпты).

---

## Известный backlog (не блокер среза, не забыть)

| Тема | Заметка |
|------|---------|
| Clarify options отжиманий | Не мешать ось «сколько раз» и «с колен/стены» в одном ряду чипов — отдельный вопрос или убрать |
| Home перегружен | Много labels (Сегодня / день / group / why); `detail` долго не показывался — в Срезе 3 частично добавили; полный declutter — с контролами / позже |
| 8 недель vs cycle 7 дней | Narrative программы vs текущий cycle — явно развести в UI на next cycle (Срез 5) |
| Strip «день N» из старых title | Промпт чинит новые create; старые draft могут содержать |
| Latency create | Path = 2 LLM calls; ~30s+ на path-фазу — резать tokens_out / few-shots; Console не даёт «ускорить schema» |
| resources/milestones | Не в structured wire — вернуть иначе, если понадобятся в продукте |
| Strategy C | Fallback без structured outputs, если снова grammar 400 |

---

## Dogfood Срез 3 (следующий шаг человека)

1. Backend restart + `alembic upgrade head` (через 007)
2. iOS rebuild если ещё не после plugins
3. Create карбонара → draft с timers (disabled) → Accept → Home Start, nudge vs alert
4. Create отжимания → counters → ± persist
5. Instant `2^100` → один LLM call, без проекта-path
6. Path-create: в audit **2** create llm_calls; **без** grammar 400

Если ок → одобрить Срез 3 → Срез 4 (Repair).

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
