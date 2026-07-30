# 03 — Scope

## Формулировка одной строкой

> Intent → полный Cycle/Path с narrative + plugins (preview) → batch clarify → Accept → live «Сегодня» по дням schedule → repair → конец цикла → детерминированный next cycle. Эталоны: карбонара, отжимания.

---

## Must have

### First-run / Path

- Полный скелет плана на draft (секции/дни/шаги/плагины), не урезанная «дразнилка»
- **Title** ответа/плана + **короткий summary** в начале тела плана (бюджет длины — см. модель)
- Описания групп (зачем фаза) — по возможности; detail у шагов — must где how-to критичен
- Batch clarify: все вопросы раунда на одном экране + optional free-text comment → один refine
- Accept = контракт (успех, горизонт/нагрузка, старт) + включение live; не первое раскрытие карты

### Runtime plugins (общие для cooking + fitness)

- **Checklist** (уже есть) — покупки / prep
- **Timer / TimerStack** — фон, nudge vs alert
- **Counter / Dose** — target/current, tap ± и/или swipe
- На create/draft: те же плагины, **контроли disabled** (preview)
- После Accept: live

### Schedule / Cycle

- Cycle first-class: horizon (напр. 7 / 14 / 30 дней — конкретные default по домену)
- Дни: `day_index` + `kind` (минимум: `train` | `rest` | `cook_session` | `other`)
- «Сегодня» привязано к дню цикла / сессии дня, не только к «следующему action в плоском списке»
- Детерминированный CTA **«Следующий цикл»** (подпись/hint от LLM опционально)
- Next cycle: prior plan + structured results прошлой недели + batch уточнения

### Repair

- Минимум: «не могу сегодня» / сдвиг / облегчённый день
- Не out of scope этого среза

### Эталоны качества

- Карбонара (односессионный / короткий cycle)
- Отжимания → ~30 (multi-day cycle)

### Сохраняем из mvp/

- Soft-start ≠ Hard Commit
- «Сегодня» / «Сделано» / «Почему сейчас» (словарь)
- Нет chat-home
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

## Приоритет внутри must (ориентир, не жёсткий waterfall)

Оба трека ценности; порядок реализации можно параллелить:

| Трек | Содержание | Зачем |
|------|------------|-------|
| A | Narrative + полный Path на draft + batch clarify + comment | First-run |
| B | Schedule/Cycle model + дни kind + Home «день N» | Программа |
| C | TimerStack + Counter (+ notifications) | Runtime ценность |
| D | Repair | Чтобы цикл не умирал |
| E | Next cycle CTA + results → N+1 | Петля тренера |

A+B+C+D+E все must для объявления среза «готово к dogfood»; внешние юзеры — после dogfood-бара.
