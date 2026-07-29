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

Auth: send `X-Device-Id: <any-stable-id>` on protected routes.
