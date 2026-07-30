# Facio client-service

FastAPI backend for the Facio MVP.

## Tests

From the repo root:

```bash
./scripts/test-client-service.sh
```

Needs Postgres (`fasio_test` on the compose instance). The script starts `fasio-postgres`, creates `fasio_test` if missing, syncs deps, and runs pytest. Extra args are passed through (`./scripts/test-client-service.sh -k create -q`).

LLM is scripted in tests (no `ANTHROPIC_API_KEY`). Coverage: schema validation, create gate (path | instant_answer), refine / restore / commit / abandon, multi-active, actions + checklist, client beacons.

## Local (Docker)

From the `fasio/` repo root:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
docker compose up --build
```

- API: http://localhost:8000
- Docs: http://localhost:8000/api/v1/docs
- Health: http://localhost:8000/health
- Logs: `apps/backend-py3/client-service/logs/fasio.log` (daily rotate, ~30 days)

Auth: send `X-Device-Id: <any-stable-id>` on protected routes.

LLM: Claude Haiku 4.5 (`LLM_MODEL`, default `claude-haiku-4-5`). Without `ANTHROPIC_API_KEY`, create/refine/repair return **501**. Create/refine/repair retry once on schema validation failure (2 attempts total).

Create prompts include a safety/policy block, grey-zone gate hints, FCT/volume caps, field glossary, and two few-shot JSON examples (path + instant_answer).

Prompt caching is on by default (`LLM_PROMPT_CACHE=true`): system + create few-shots get `cache_control` (TTL `LLM_PROMPT_CACHE_TTL`: `5m` or `1h`). Disable with `LLM_PROMPT_CACHE=false`.

### Create intent (`POST /api/v1/projects`)

Response is a discriminated union:

- `{"kind": "path", "project": {...}}` — draft Path created (`soft_start_shown` + `draft_shown` server events)
- `{"kind": "instant_answer", "label", "answer", "goal_suggestions", ...}` — not a Facio project; no Project row; chronology stored under `user_id`

```bash
# Likely path
curl -s -X POST http://localhost:8000/api/v1/projects \
  -H 'Content-Type: application/json' \
  -H 'X-Device-Id: demo' \
  -d '{"intent":"Приготовить карбонару"}'

# Likely instant answer (no project)
curl -s -X POST http://localhost:8000/api/v1/projects \
  -H 'Content-Type: application/json' \
  -H 'X-Device-Id: demo' \
  -d '{"intent":"Сколько будет 2 в 100 степени?"}'
```

### Client events (`POST /api/v1/events`)

UI beacons only: `app_opened`, `accept_viewed`, `action_shown`, `path_opened`, `project_switched`.  
Mutation facts (`intent_submitted`, `committed`, `action_done`, …) are written by the server — do not re-post them.

### Metrics views

After `alembic upgrade head`: `mvp_activation_kpis`, `mvp_fct`, `mvp_event_counts`, `mvp_domain_counts`, … (see `docs/mvp/04-metrics.md`).

### Archive

- `POST /api/v1/projects/{id}/abandon` — draft|active → abandoned  
- `GET /api/v1/projects?status=abandoned` — archive list only  
- default `?status=open` — Home (excludes abandoned)

Admin history routes (`transcript` / `timeline`) are removed from the HTTP API (service helpers remain). `GET /projects/{id}/state-versions` is available for draft «Назад».

`GET /projects` and `GET /projects/{id}` include `next_action` (null unless status is active with a pending step).

### Schema reset after migration squash

Alembic history was squashed into a single `001_initial`. Recreate the volume:

```bash
docker compose down -v
docker compose up --build
```
