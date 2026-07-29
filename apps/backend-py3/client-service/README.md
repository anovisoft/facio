# Facio client-service

FastAPI backend for the Facio MVP.

## Local (Docker)

From the `fasio/` repo root:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
docker compose up --build
```

- API: http://localhost:8000
- Docs: http://localhost:8000/api/v1/docs
- Health: http://localhost:8000/health
- Timeline (audit chronology): `GET /api/v1/projects/{id}/timeline`

Auth: send `X-Device-Id: <any-stable-id>` on protected routes.

LLM: Claude Sonnet 5 (`LLM_MODEL`, default `claude-sonnet-5`). Without `ANTHROPIC_API_KEY`, create/refine/repair return **501**.

Create prompts include a safety/policy block, grey-zone gate hints, FCT/volume caps, field glossary, and two few-shot JSON examples (path + instant_answer).

Prompt caching is on by default (`LLM_PROMPT_CACHE=true`): system + create few-shots get `cache_control` (TTL `LLM_PROMPT_CACHE_TTL`: `5m` or `1h`). Disable with `LLM_PROMPT_CACHE=false`.

### Create intent (`POST /api/v1/projects`)

Response is a discriminated union:

- `{"kind": "path", "project": {...}}` — draft Path created
- `{"kind": "instant_answer", "label", "answer", "goal_suggestions", ...}` — not a Facio project; no Project row; full chronology stored under `user_id`

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

### Schema reset after migration squash

Alembic history was squashed into a single `001_initial`. Recreate the volume:

```bash
docker compose down -v
docker compose up --build
```
