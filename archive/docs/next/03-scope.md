# 03 — Scope

## Формулировка одной строкой

> Intent → быстрый slim-старт (смысл + вопросы) → полный Cycle/Path с plugins доезжает → правки на живом плане (batch clarify / repair) → «Сегодня» по schedule → конец цикла → детерминированный next cycle. Эталоны: карбонара, отжимания.

**Устаревает:** жёсткий конвейер Draft → Accept (дубль карты) → live. См. [05](./05-ux-flows.md), [09](./09-continuity.md).

---

## Must have

### First-run / Path

- Быстрый первый кадр (slim): paraphrase/title/summary + batch questions; полный Path+plugins может доезжать
- Полный исполняемый скелет на плане (секции/дни/шаги/плагины), не «дразнилка до Accept»
- **Title** ответа/плана + **короткий summary** в начале тела плана
- Описания групп (зачем фаза) — по возможности; detail у шагов — must где how-to критичен
- Batch clarify: все вопросы раунда на одном экране + optional free-text comment → один refine
- Один живой план: правка структуры всегда; «начать сегодня» вместо тяжёлого Accept-дубля

### Runtime plugins (общие для cooking + fitness)

- **Checklist** (уже есть) — покупки / prep
- **Clock family:** TimerStack + **Timeline** (готовка) + **Interval** (HIIT по sec) + **Stepper/set_plan** (силовая: measure/work/rest + counter на beat)
- **Counter / Dose** — одиночный или внутри stepper beat
- Checklist — покупки/бинарное; **не** подходы в зале
- Home = **Session Stage** (shape герой); бургер → весь план
- На плане: hints; live после Start (#3)

### Schedule / Cycle

- Cycle first-class: horizon (напр. 7 / 14 / 30 дней — конкретные default по домену)
- Дни: `day_index` + `kind` (минимум: `train` | `rest` | `cook_session` | `other`)
- **Физический день (must):** «Сегодня» привязано к календарю от якоря цикла (`committed_at` / first_step_when). Закрытие дня N не открывает execute дня N+1 до следующего calendar day. **Следующие дни можно смотреть** (карта / весь план), но не закрывать и не запускать plugins
- «Сегодня» = день цикла / сессия дня в пределах unlocked window
- Детерминированный CTA **«Следующий цикл»** (подпись/hint от LLM опционально)
- Next cycle: prior plan + structured results прошлой недели + batch уточнения

### Repair

- Минимум: «не могу сегодня» / сдвиг / облегчённый день — на фоне **физического дня**
- Тот же класс мутаций, что refine — на живом плане, не отдельный «мир после Accept»
- Не out of scope этого среза

### Эталоны качества

- Карбонара (односессионный / короткий cycle) — целевой clock: **timeline**
- Отжимания → ~30 (multi-day cycle) — counters; interval_plan где круговая сессия

### Сохраняем из mvp/

- Soft-start ≠ бесконечная пустота до ответа
- «Сегодня» / «Сделано» / «Почему сейчас» (словарь)
- Нет chat-home (операции под капотом ок)
- Multi-active проекты
- Audit / state versions на create/refine/repair/next-cycle

---

## Should have

- Недельный мини-обзор прогресса цикла
- Более богатый evidence (фото блюда / лог подходов)
- Мягкий focus среди multi-active
- Гибкий scheduler «N раз/неделю в любые дни» (после явной карты дней)

---

## Out of scope (этот срез)

- Свободный UI-конструктор / LLM-виджеты вне закрытого enum plugins
- Chat как главная поверхность; «спроси ИИ» как единственный способ продлить цикл
- Полноценный Blueprint DSL / VectorDB / marketplace
- Монетизация / App Store как цель среза
- Широкий внешний юзер-тест **текущего** POC-билда
- Медицинские / sensitive domains как поддерживаемые
- Произвольный «любой intent» с тем же качеством, что эталоны

---

## Приоритет внутри must (ориентир)

| Трек | Содержание | Зачем |
|------|------------|-------|
| A | Narrative + полный Path + batch clarify + comment | First-run |
| B | Schedule/Cycle model + дни kind + Home «день N» | Программа |
| C | TimerStack + Counter (+ notifications) | Runtime база |
| C′ | Progressive slim create; Timeline + Interval | Ощущение + юзабельность clock |
| D | Repair на живом плане (без Draft/Accept-дубля) | Цикл не умирает |
| E | Next cycle CTA + results → N+1 | Петля тренера |

A–C в коде/dogfood; C′+D+E — следующие. Внешние юзеры — после dogfood-бара.
