# Facio Next — от POC к исполняемому циклу

Документы этого каталога фиксируют **следующий продуктовый срез** после текущего билда в `apps/`.

| Слой | Роль |
|------|------|
| [`../RFC/`](../RFC/README.md) | Долгосрочная архитектура и философия |
| [`../mvp/`](../mvp/README.md) | Первый эксперимент: soft-start, Path, «Сегодня», audit |
| **`next/`** | Принятый **engine**-этап: cycles, plugins, physical day, repair, next cycle |
| [`../Facio 0.1/`](../Facio%200.1/README.md) | **Актуальная точка истины** продукта (позиционирование, IA, экраны) |

Текущий билд по итогам срезов 1–5 — **принятый этап** `next/` (карбонара dogfood ок; полный fitness multi-day бар отложен из‑за physical day). Детали — [09](./09-continuity.md).

> Для новой реализации UX/навигации/терминов читать **Facio 0.1**. Этот каталог — как собран runtime; поверхность Continue / Guide / Session описана там.

---

## Читать по порядку

1. [01 — Диагноз](./01-diagnosis.md) — почему нет ценности и что меняем
2. [02 — Цели и гипотезы](./02-goals-hypotheses.md) — что считаем успехом этого среза
3. [03 — Scope](./03-scope.md) — must / should / out
4. [04 — Модель](./04-model.md) — план-контент, cycle, schedule, plugins (**stepper**)
5. [05 — UX и потоки](./05-ux-flows.md) — Session Stage Home, бургер→план, draft, repair
6. [06 — Эталоны](./06-reference-scenarios.md) — карбонара и отжимания
7. [07 — Тестирование](./07-testing-stance.md) — когда внешние юзеры, что до
8. [08 — План реализации](./08-impl-plan.md) — срезы 1–5 **приняты**; дальше polish / time travel
9. [09 — Continuity](./09-continuity.md) — приёмка этапа, backlog, решения A–F

---

## Одно предложение

> Facio показывает **программу на цикл** (короткий смысл + карта дней + исполняемые шаги), даёт пройти её с таймерами/каунтерами и **одним жестом открыть следующий цикл** на базе фактов прошлого — с уточнениями, не с нуля.

Центр: не «AI написал список», а **Plan as Runtime Artifact** — то же, что видишь на create, исполняешь в «Сегодня»; цикл — единица прогресса.

Не чат. Продление цикла — **детерминированный CTA**; copy может подсказать модель.

---

## Связь с решениями обсуждения

Зафиксировано:

- Полный маршрут не прячется «до Accept»; **Draft → Accept → live как жёсткий конвейер устарел** — живой план + мутации.
- Progressive create: **#1** start → **#2** Path+hints → **#3** plugins after Start.
- Draft UX: compact outline + sticky CTA + comment always.
- **Home = Session Stage** (timeline/stepper герой ~2/3); **бургер справа сверху → весь план**.
- Stepper: measure/work/rest beats; силовая = один session action; не checklist подходов.
- CTA: «Сохранить и приступить» / «Сохранить»; без сегодня/завтра.
- Timeline XOR timers; clock family + stepper; hints → live #3.
- Физический день + preview locked.
- Batch clarify + comment; Repair; cycles → next cycle.
- Wedge: карбонара + отжимания. Внешний юзер-тест — рано.
- Рабочая память: [09 — Continuity](./09-continuity.md).
