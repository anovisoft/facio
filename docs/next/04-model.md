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

Лёгкий schedule сразу (не Google Calendar). Нужен для reuse циклов.

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

- `day_offset` / `day_index` остаются совместимой идеей «день от старта цикла».
- Kind и session делают поведение дней **разным** в UI.

«N раз в неделю в любые дни» — should later; для среза важна **явная карта дней**.

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

### timer_stack

```text
timers[]
  id
  title                 # «Лапша», «Помешать»
  duration_sec
  signal                # nudge | alert
  parallel_group?       # параллельные таймеры готовки
```

- Работают в фоне после старта (live mode).
- **nudge** — короткий/нейтральный (вибро / тихий звук) для дробных.
- **alert** — нельзя пропустить (критичное событие).

### counter / dose

```text
counter
  label?                # «подходы», «повторы»
  target
  current               # 0 на create
  step?                 # инкремент, default 1
```

UX: tap ± и/или swipe (как seek в плеере).

### Режим preview vs live

| | draft / Accept до commit | после Accept |
|--|--------------------------|--------------|
| Рендер | полный, как в runtime | тот же |
| Контролы | disabled / не стартуют | live |
| Уведомления таймеров | нет | да (с permission) |

LLM на create **обязан** ставить plugins там, где эталон без них бессмысленен.

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

---

## 9. Явный non-goal модели

- Произвольные вложенные экраны от LLM
- Плагины вне enum без обновления клиента
- Продление цикла только через свободный чат
- Один бесконечный Path без границ cycle
