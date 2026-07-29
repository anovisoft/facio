# 02 — Состав MVP

## Формулировка scope одной строкой

> Intent → **soft-start + draft Path + уточнения** (назад/пересбор) → достаточный Path + **Принять путь** → N active-проектов → Home **«Сегодня»** + hero **«Почему сейчас»** + **Весь путь** → **Сделано**. Без chat-home. LLM на create/repair. Максимальный audit trail.

---

## Must have (входит)

### Продукт / UX

- Поле **«Что вы хотите сделать?»** + примеры
- **Soft-start + comprehension**: paraphrase цели сразу после intent (не hard Commit)
- Сразу **черновик Path** + 2–4 уточнения (chips / свой ответ)
- **Назад / доуточнить / пересобрать** до принятия
- Перед принятием — **достаточный полный Path** (готовка: продукты + как готовить) + контракт
- Hard Commit: **«Принять путь» / «Начинаю»** + когда первый шаг
- **Несколько active** проектов
- Home: одно **«Сегодня»**; кнопки **«Сделано»** / **«Пропустить»** (не Done/Action в UI)
- **«Почему сейчас»** — hero-блок, `why` обязателен в schema
- Кнопка **«Весь путь»** после старта
- First Completion после первого «Сделано»
- Нет вкладки Chat как главной поверхности

### Данные / модель

База + группы + чеклист — см. подробно [07-additional-path-structure.md](./07-additional-path-structure.md).

```text
outcome                 # + paraphrase для soft-start
success_criteria
horizon
groups[]                # секции Path: «Покупки», «Готовка», …
actions[]               # title, why (required), detail, estimate_min, day_offset/due, group_id?
  checklist_items[]?    # пункты внутри шага (яйца ☐ …)
resources[]             # optional
milestones[]            # optional
```

Пустой `why` → не принимать state.

### Персистентность (критично)

См. `05-tech-slice.md`: turns, llm_calls (prompt+raw), state_versions, events — с дня 1, по максимуму.

### Техника

- Expo/RN — iOS ship у команды отработан  
- FastAPI + PostgreSQL  
- device_id / простой auth  
- LLM structured output + validate + retry  

---

## Should have

- Repair «сдвинуть / пересчитать»
- Напоминания на due
- История «Сделано»
- Мягкий focus среди multi-active
- Metabase/SQL воронка

---

## Out of scope

- Chat-home / AI-собеседник вкладка  
- Hard Commit *до* Path как единственный commit  
- Blueprint DSL / VectorDB / Coach billing / Marketplace  
- Принудительный single-active  
- Offline CRDT  
- Монетизация в этом эксперименте (не проверяем)  
- Публичный App Store как цель недели  
- Sensitive domains как поддерживаемые  

---

## Связь с RFC

| RFC / идея | MVP |
|------------|-----|
| Next step + why | Да, центр UI |
| Path disclosure | Да, draft→full→expand |
| Soft-start ≠ hard commit | Да |
| Multi-project | Да |
| Audit trail | Да |
| Monetization test | Нет |
| Blueprint compiler | Нет (LLM→schema) |
