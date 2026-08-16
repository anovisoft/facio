# Facio talk

FastAPI. Accepts a desk snapshot and an utterance, returns a validated patch.

The model key stays on this process. The lid does not need this service to open Today or tick a widget.

## Docker (preferred)

From the repo root:

```bash
docker compose up --build
```

Simulator talks to `http://127.0.0.1:8000`. Default mode is `scripted` (goldens, no paid key).

Live model — env on the host, not in the image:

```bash
FACIO_TALK_MODE=live FACIO_MODEL_API_KEY=... docker compose up --build
```

## Local venv

```bash
cd apps/api
python3 -m venv .venv
source .venv/bin/activate
pip install -e ../../packages/domain -e ".[dev]"
fastapi dev
```
