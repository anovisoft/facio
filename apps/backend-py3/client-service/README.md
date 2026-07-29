# Facio client-service

FastAPI backend for the Facio MVP.

## Local (Docker)

From the `fasio/` repo root:

```bash
docker compose up --build
```

- API: http://localhost:8000
- Docs: http://localhost:8000/api/v1/docs
- Health: http://localhost:8000/health
- Timeline (audit chronology): `GET /api/v1/projects/{id}/timeline`

Auth: send `X-Device-Id: <any-stable-id>` on protected routes.

### Schema reset after migration squash

Alembic history was squashed into a single `001_initial`. Recreate the volume:

```bash
docker compose down -v
docker compose up --build
```
