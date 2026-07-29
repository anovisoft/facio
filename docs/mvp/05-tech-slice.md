# 05 — Технический срез

Ориентир: fullstack + AI-кодинг, **~2–3 дня** на вертикальный срез.  
**RN → iOS у команды уже деплоился** — ship на устройство не закладываем как отдельный риск/пожиратель дней.

## Стек

| Слой | Выбор |
|------|--------|
| Mobile | Expo / React Native (привычный пайплайн команды) |
| API | FastAPI |
| DB | PostgreSQL |
| LLM | structured JSON output |
| Auth | `device_id` / простой auth |
| Deploy API | Railway / Fly / Render |

LLM в daily loop выключен. Включён на draft create, refine/recompute и опционально repair.

UI-copy: **Сегодня / Сделано / Почему сейчас / Принять путь**. В схеме БД поле может оставаться `actions` / `status=done`.


---

## Таблицы

### Runtime

- `users` — id, device_id, created_at  
- `projects` — user_id, status (`draft`/`active`/`abandoned`/`completed`), raw_intent, outcome, success_criteria, horizon, committed_at, **много active на user допустимо**  
- `actions` — project_id, title, why, **detail**, estimate_min, due_at, sort, status  

### Audit / обучение (must, «по максимуму»)

- `conversation_turns` — project_id (nullable до create), role (`user`/`assistant`/`system`), content, created_at, meta  
- `llm_calls` — project_id, purpose (`create`/`repair`/…), model, **prompt_messages jsonb**, **raw_response text/jsonb**, parsed_ok, tokens_in/out, latency_ms, error, created_at  
- `state_versions` — project_id, version, **state_json**, source (`llm_create`/`llm_repair`/`user_edit`/`shift`), created_at  
- `events` — type, user_id, project_id, payload jsonb, created_at  
- `action_audit` (или events) — каждое complete/skip/reschedule с previous/new  

Правило: **не затирать** сырой ответ модели после parse. Хранить и raw, и нормализованный state.

Retention: для MVP — не удалять; позже политика privacy/GDPR, но default = keep for learning.

---

## API

```text
GET  /projects                    # список (multi active)
POST /projects                    # intent → LLM → path | instant_answer
GET  /projects/{id}               # contract + state summary
GET  /projects/{id}/actions       # полный Path
GET  /projects/{id}/next-action
POST /projects/{id}/commit
POST /actions/{id}/complete
POST /actions/{id}/skip
POST /projects/{id}/repair        # optional
GET  /projects/{id}/transcript    # optional debug/admin
```

`GET /projects/active` → заменить/дополнить списком всех non-abandoned.

---

## Create pipeline

```text
persist intent_submitted + user turn (user_id, project_id=null)
  → LLM create (Claude Sonnet 5, structured JSON)
       • kind=instant_answer → assistant turn + instant_answer_shown
         (no Project; chronology queryable by user_id)
       • kind=path → create Project draft + state_versions + draft_shown
  → refine loop: each answer → new llm_call + new state version
  → Accept screen: full path
commit → active (другие active не трогаем)
```

Env: `ANTHROPIC_API_KEY`, optional `LLM_MODEL` (default `claude-sonnet-5`).

---

## iOS

Не блокер: используем существующий опыт RN deploy / TestFlight / EAS.  
Фокус дней — продукт (multi-project, Path, persistence), не «впервые выйти на iPhone».

---

## Не строить в эти дни

pgvector, blueprint YAML compiler, subscriptions, chat-вкладка, offline CRDT.
