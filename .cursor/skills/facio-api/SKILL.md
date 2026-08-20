---
name: facio-api
description: Facio FastAPI talk service conventions. Use when creating, editing, or reviewing apps/api, talk tools, patch validation, eval harness, or wiring facio_domain into HTTP.
---

# Facio API

Before writing the service, read:

1. This file
2. `.cursor/skills/facio-product/SKILL.md`
3. `.cursor/skills/fastapi/SKILL.md`
4. `.cursor/skills/pytest-patterns/SKILL.md` when adding tests

Do **not** follow `.cursor/skills/fastapi-templates/` in **В1–В2** — that layout assumes DB, JWT, CRUD layers from day one. **В3 may use it** for Postgres session, repositories, and account/desk wiring. Still: one package, law in `facio_domain`, no broker «на вырост», no second repo, Sign in with Apple not generic users CRUD. Do **not** keep the step-4 stub: after **В1.0**, `facio_api` is a service package (`main` factory, `config`, `routers`, `talk`, `providers`; later `mcp`, then `accounts` / `desk` / `jobs`).

## Shape

- Package: `apps/api`, entry `facio_api`. Depend on `facio_domain`.
- Talk is the job until wave 3: accept a desk snapshot + utterance, return a validated patch and assistant text. Wave 3 adds server of record, Sign in with Apple, push jobs — still this app, not a second repo.
- Model key stays on the server. The client never sees it.
- No Postgres, vector index, broker, or RAG until wave **В3**. Wave 1 talk stays snapshot-in / validated desk-out. **В1.0–В1.4 done; В1.5 next** (live harness). MCP is `facio_api.mcp` (stdio, same 16 names, `apply_tool`). Do not add empty `accounts/` / `desk/` / `jobs/` before those steps.
- Lid execute stays on device. This service must not be required to open Today or tick a widget.

## Tools and patches

Tools are exactly the conceptual set in [`docs/rfc/05-ai-and-memory.md`](../../../docs/rfc/05-ai-and-memory.md). Unvalidated model text never becomes widget payload. A cue without `surface` is rejected.

Pain policy runs **before** tools: if the turn reports pain, refuse any raise of target or cadence.

## Eval

Golden utterances → expected tool calls and resulting desk. Required before widening the tool loop (RFC Q22). Files live in `apps/api/goldens`. Prefer fixture subjects from `packages/domain/fixtures`.

Default `FACIO_TALK_MODE=scripted` so the founding turns run without a paid key. Live mode: `FACIO_MODEL_NAME` selects the vendor (`gpt-4o-mini` / `gpt` → OpenAI, `haiku` / `claude-haiku-4-5` → Anthropic Haiku). Only the matching key is required (`FACIO_OPENAI_API_KEY` or `FACIO_ANTHROPIC_API_KEY`); the other may be empty. Keys stay on the server.

Run locally with Compose from the repo root (`docker compose up --build`). One service, port 8000. Copy `apps/api/.env.example` to `.env` (compose) and/or `apps/api/.env` (`fastapi dev`). Do not copy `archive/docker-compose.yml` (Postgres). In the image, goldens are `FACIO_GOLDENS_DIR`. `fastapi dev` needs `fastapi[standard]`.

## Tests

Keep `facio_domain` tests as the law. API tests cover validation, pain gate, and goldens; from В1.0 also router wiring. Mock the model provider; do not mock domain arithmetic. Wave 3 adds integration tests against a test database — still not a mocked ORM.
