# 04 — Модель

Клиент рендерит **известные** типы. LLM заполняет schema. Не свободный конструктор.

Наследует идеи `mvp/07` и RFC Execution/Blueprint, но поднимает **Cycle** и **plugins** в first-class.

---

## 1. Plan content (narrative)

Минимум, чтобы план не был голым списком:

```text
title                 # заголовок плана / ответа ИИ (hero)
summary               # 1–3 предложения в начале тела
                      # пример: «За ~8 недель — к 30 отжиманиям. Эта неделя — база…»
outcome               # контрактная цель (может совпадать/уточнять title)
paraphrase            # soft-start строка
success_criteria
horizon               # человекочитаемо; связано с cycle.horizon_days
```

Бюджет длины (ориентир для validate/prompts):

| Поле | Бюджет |
|------|--------|
| title | коротко, ~1 строка |
| summary | 1–3 предложения |
| group.description | 1–2 предложения |
| action.detail | how-to, не эссе |
| action.why | 1–2 предложения (hero «Почему сейчас») |

Пустой `summary` на create для эталонов — нежелателен (reject или retry в промпте).

---

## 2. Groups

```text
groups[]
  id
  title
  description?        # зачем эта фаза / секция
  sort
```

Группы могут соответствовать фазам готовки («Покупки», «Готовка») или блокам программы.  
Карта **дней** — не замена groups; см. schedule.

---

## 3. Cycle (first-class)

```text
cycle
  id
  index               # 1, 2, … внутри project
  horizon_days        # 7 | 14 | 30 | … (default по домену)
  status              # draft | active | completed | abandoned
  goal_for_cycle?     # опционально: цель именно этого цикла
```

Инварианты:

- Project имеет **текущий** cycle; история циклов сохраняется.
- «Продлить» создаёт новый cycle, а не дописывает actions в бесконечный Path без границы.
- Результаты цикла — structured summary для next-cycle prompt (не сырой чат-лог).

Defaults (ориентир):

| Домен / эталон | Default horizon |
|----------------|-----------------|
| Карбонара | 1 день / одна cook_session (короткий cycle) |
| Отжимания | 7 дней (потом 7/14 по результатам) |

---

## 4. Schedule

Лёгкий schedule (не Google Calendar sync). Нужен для reuse циклов **и** для физического ритма.

```text
days[]
  day_index           # 0 .. horizon_days-1
  kind                # train | rest | cook_session | other
  title?              # «Силовая A», «Отдых + мобилити»
  summary?            # коротко, что сегодня за день
  session_steps[]     # упорядоченные шаги/плагины дня
    → ссылки на actions / inline steps
```

Связь с прежним `day_offset`:

- `day_offset` / `day_index` = слот программы внутри цикла.
- Kind и session делают поведение дней **разным** в UI.

### Физический день (must, Срез 4)

Программный день ≠ «можно прокликать весь цикл за вечер».

```text
cycle_anchor_date     # calendar date старта: commit today → D0; first_step_when=tomorrow → D0 завтра
local_today           # календарная дата пользователя (клиент → API; fallback UTC date)
unlocked_day_index    # local < anchor → -1 (ничего); else min(delta, horizon-1)

focus_day:
  earliest pending day_index <= unlocked_day_index   # catch-up ок; при -1 focus пуст
  иначе waiting / peek на Home                       # нельзя забежать вперёд по действиям
```

- Закрыл день 0 утром → день 1 **не** становится исполняемым «Сегодня» до следующего calendar day.
- `first_step_when=tomorrow`: в день commit execute закрыт (unlocked=-1), день 0 только peek до anchor.
- Отставание: focus остаётся на незакрытом прошлом дне (не прыгаем на unlocked).
- **Preview будущих дней — must:** карта плана и «Весь план» показывают дни `> unlocked` (titles, kind, steps, plugin hints). Контролы complete/skip/timer/counter/interval **disabled**; нельзя закрыть/выполнить locked day.
- Home: focus = unlocked/catch-up день; будущие / pre-anchor — peek, не execute.
- Карбонара `horizon_days=1` + commit today: unlocked=0 — поведение как сейчас.
- Repair («не могу сегодня») сдвигает/облегчает **относительно физического сегодня**, иначе жест пустой.

«N раз в неделю в любые дни» — should later; для среза важна **явная карта дней + calendar unlock + preview-locked**.

---

## 5. Action / step + plugins

Шаг по-прежнему имеет:

```text
id, title, why, detail?, estimate_min?, group_id?, sort, status
```

Плюс **закрытый** набор plugins (0..N на шаг или шаг = один plugin-host):

### checklist (есть)

```text
checklist_items[]: { id, title, done, sort }
```

**Когда:** покупки, сборы, бинарные «сделал/не».  
**Не когда:** подходы в зале («Подход 1/2/3») — это не галочки. Для силовой → **stepper**.

### Clock family (runtime часов)

Один движок времени на клиенте (elapsed, pause/resume, complete segment/marker, фон + сигналы). LLM выбирает **shape**, не произвольный виджет.

Home рендерит shape как **Session Stage** (герой экрана), не виджет под буклетом. См. [05](./05-ux-flows.md) Session Stage.

#### timer_stack (есть)

```text
timers[]
  id, title, duration_sec, signal  # nudge | alert
  parallel_group?
```

Изолированный отсчёт с ручным Start — где **нет** единой оси сессии. XOR с timeline на одном action.

#### timeline (карбонара / cook)

```text
timeline
  duration_sec
  markers[]: { at_sec, title, signal }
```

Дробные «помешать» = маркеры оси, не peer-таймеры. **UI:** Timeline = Session Stage.

**Prep ≠ axis:** mise / ножевая работа (нарезать, сыр, желтки) — отдельный **checklist**-action **до** cook-сессии, `plugin_hints=[]`. Timeline t=0 = жар / кипяток / критичная ось — **не** «нарезать».

#### interval_plan (HIIT по секундам)

```text
interval_plan
  segments[]: { duration_sec, title, signal? }
```

Когда work/rest заданы **секундами** (Табата), не числом повторов.

#### stepper / set_plan (зал: подходы + отдых + замер) — must

Одна силовая сессия = **один action** дня (не дробить max+volume). Внутри — биты:

```text
stepper   # wire: stepper (JSONB на action); hint "stepper"
  beats[]
    id
    kind          # measure | work | rest
    title
    counter?      # work/measure: { label?, target?, current, step? }
    duration_sec? # rest: таймер отдыха
    signal?
```

Пример: measure → rest 5м → work (counter 12–15) → rest 2–3м → work → …

**Запрещено:** checklist «Подход N» + один общий counter на action.  
**Запрещено:** несколько голых counters без оркестрации отдыха.  
#2: `plugin_hints: ["stepper"]`; #3: полные beats.

### counter / dose (одиночный)

```text
counter: { label?, target, current, step? }
```

Только вне серии подходов. В силовой counter живёт **внутри beat**.

### Режим preview vs live

Один живой план; preview/live = сессия не начата / идёт. См. [05](./05-ux-flows.md), [09](./09-continuity.md).

| | до старта | сессия |
|--|-----------|--------|
| Stage | полный shape | live + pause где есть |
| Support | title + коротко | «Сейчас: …» |
| Уведомления | нет | да |

LLM **обязан** выбрать shape: cook → **timeline**; силовая с подходами → **stepper**; HIIT по sec → **interval_plan**; покупки → **checklist**.

---

## 6. Clarify (batch)

```text
questions[]             # 0 или 2–4 за раунд (как сейчас в schema-духе)
  id, prompt, options[]

# На submit refine:
answers[]: { question_id, value }
comment?                # свободный комментарий ко всему раунду
```

UI показывает **все** вопросы раунда; не только `questions[0]`.

---

## 7. Cycle results → next cycle

Структурированный итог (минимум):

```text
cycle_result
  completed_steps
  skipped_steps
  partial_notes?        # самооценка / «сделал 60%»
  counters_snapshot?    # факты доз
  user_comment?
```

Next cycle input = prior cycle plan + `cycle_result` + batch clarify answers.

CTA: детерминированная кнопка «Следующий цикл».  
Опционально: `continue_label` от модели («Продолжить тренировки») — только copy.

---

## 8. Repair (минимум модели)

Операции уровня продукта (детали API — на реализации):

- сдвиг дня / оставшихся дней
- заменить день на облегчённый / rest
- уменьшить dose (counters / объём)

Все — versioned state; audit как в mvp.  
Тот же класс мутаций, что refine на **живом** плане — не отдельный мир «только после Accept». См. [09](./09-continuity.md) решение A.

**Сейчас в коде:** `RepairIntent = shift | lighten | rest` + optional `reason`.  
**Future:** free-text comment в UI; intent set **по domain** (cook ≠ fitness). Подробности — [05 Repair future](./05-ux-flows.md) + backlog [09](./09-continuity.md).

---

## 9. Явный non-goal модели

- Произвольные вложенные экраны от LLM
- Плагины вне enum без обновления клиента
- Продление цикла только через свободный чат
- Один бесконечный Path без границ cycle
