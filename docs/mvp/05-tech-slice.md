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
- `projects` — user_id, status (`draft`/`active`/`abandoned`/`completed`), raw_intent, outcome, success_criteria, horizon, domain, tags, committed_at, **много active на user допустимо**  
- `actions` — project_id, title, why, **detail**, estimate_min, due_at, sort, status  

### Audit / обучение (must, «по максимуму»)

- `conversation_turns` — user_id, project_id (nullable для instant_answer), role (`user`/`assistant`/`system`), content, created_at, meta  
- `llm_calls` — user_id, project_id, purpose (`create`/`refine`/`repair`), model, **prompt_messages jsonb**, **raw_response text/jsonb**, parsed_ok, tokens_in/out, latency_ms, error, created_at  
- `state_versions` — project_id, version, **state_json**, source (`llm_create` / `llm_refine` / `llm_repair` / `user_restore`), created_at  
- `events` — type, user_id, project_id, payload jsonb, created_at  

`source` на практике:

| source | Когда |
|--------|--------|
| `llm_create` | первый Path после intent |
| `llm_refine` | ответ на уточнение / пересбор draft |
| `llm_repair` | «не могу / сдвинуть» (draft или active) |
| `user_restore` | «Назад» — откат к прошлому `state_versions.version` |

Отдельной таблицы `action_audit` нет: complete / skip / checklist toggle пишутся в `events` с `previous_*` / `new_*` в payload.

Правило: **не затирать** сырой ответ модели после parse. Хранить и raw, и нормализованный state.

Retention: для MVP — не удалять; позже политика privacy/GDPR, но default = keep for learning.

### Метрики (SQL views)

Alembic `003_mvp_metric_views` + `004` (`mvp_domain_counts`): `mvp_event_counts`, `mvp_project_milestones`, `mvp_fct`, `mvp_activation_kpis`, `mvp_user_project_stats`, `mvp_audit_gaps`, `mvp_domain_counts`. См. `04-metrics.md`.

---

## API

```text
GET  /projects                    # ?status=open|abandoned|draft|active|completed
POST /projects                    # intent → LLM → path | instant_answer
GET  /projects/{id}               # contract + state summary
GET  /projects/{id}/actions       # полный Path
GET  /projects/{id}/next-action
POST /projects/{id}/refine
POST /projects/{id}/commit
POST /projects/{id}/abandon       # draft|active → abandoned (архив)
POST /projects/{id}/restore-state # «Назад» к version (draft)
POST /projects/{id}/repair        # optional
POST /actions/{id}/complete
POST /actions/{id}/skip
POST /checklist-items/{id}/toggle
POST /events                      # UI beacons only (см. ниже)
```

Admin/debug history routes (`transcript` / `timeline` / `state-versions`) removed from the HTTP surface; service methods remain for future admin tooling. Restore from git if needed.

`GET /projects/active` → заменить/дополнить списком всех non-abandoned.

### Events ownership

**Сервер** пишет факты мутаций: `intent_submitted`, `soft_start_shown`, `draft_shown`, `instant_answer_shown`, `refine_answered`, `back_navigated`, `plan_failed`, `committed`, `action_done`, `action_skipped`, `first_completion`, `repair_*`, `checklist_item_toggled`, `project_completed`, `project_abandoned`.

**Клиент** (`POST /events`) — только показы UI: `app_opened`, `accept_viewed`, `action_shown`, `path_opened`, `project_switched`.  
Не дублировать серверные типы — иначе KPI в `04` двойной учёт.

---

## Create pipeline

```text
persist intent_submitted + user turn (user_id, project_id=null)
  → LLM create (Claude Sonnet 5, structured JSON; validate + до 2 попыток)
       • kind=instant_answer → assistant turn + instant_answer_shown
         (no Project; audit rows by user_id)
       • kind=path → create Project draft + state_versions
         + soft_start_shown + draft_shown (same create composition; both server)
         (intent event/turn получают project_id)
  → refine loop: each answer → new llm_call + new state version (retry ×2)
  → Accept screen: full path (client beacon accept_viewed)
commit → active (другие active не трогаем)
```

Env: `ANTHROPIC_API_KEY`, optional `LLM_MODEL` (default `claude-sonnet-5`).  
Logs: `LOG_DIR` (default `logs`), daily rotate, `LOG_BACKUP_COUNT=30`.

---

## iOS

Не блокер: используем существующий опыт RN deploy / TestFlight / EAS.  
Фокус дней — продукт (multi-project, Path, persistence), не «впервые выйти на iPhone».

---

## Не строить в эти дни

pgvector, blueprint YAML compiler, subscriptions, chat-вкладка, offline CRDT.
