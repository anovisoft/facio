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

Do **not** follow `.cursor/skills/fastapi-templates/` — that layout is too large for this service.

## Shape

- Package: `apps/api`, entry `facio_api`. Depend on `facio_domain`.
- Talk is the job: accept a desk snapshot + utterance, return a validated patch and assistant text.
- Model key stays on the server. The client never sees it.
- No Postgres, vector index, broker, or RAG in v1.
- Lid execute stays on device. This service must not be required to open Today or tick a widget.

## Tools and patches

Tools are exactly the conceptual set in [`docs/rfc/05-ai-and-memory.md`](../../../docs/rfc/05-ai-and-memory.md). Unvalidated model text never becomes widget payload. A cue without `surface` is rejected.

Pain policy runs **before** tools: if the turn reports pain, refuse any raise of target or cadence.

## Eval

Golden utterances → expected tool calls and resulting desk. Required before widening the tool loop (RFC Q22). Files live in `apps/api/goldens`. Prefer fixture subjects from `packages/domain/fixtures`.

Default `FACIO_TALK_MODE=scripted` so the founding turns run without a paid key. Live mode needs `FACIO_MODEL_API_KEY` on the server only.

Run locally with Compose from the repo root (`docker compose up --build`). One service, port 8000. Do not copy `archive/docker-compose.yml` (Postgres). In the image, goldens are `FACIO_GOLDENS_DIR`. `fastapi dev` needs `fastapi[standard]`.

## Tests

Keep `facio_domain` tests as the law. API tests cover validation, pain gate, and goldens. Mock the model provider; do not mock domain arithmetic.
