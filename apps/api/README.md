# Facio talk

FastAPI. Accepts a desk snapshot and an utterance, returns a validated patch.

The model key stays on this process. The lid does not need this service to open Today or tick a widget.

Package layout: `create_app()` in `main.py`, HTTP in `routers/` (health and talk), the turn loop in `talk/`, vendors in `providers/`. Phone contract is `GET /v1/health` and `POST /v1/talk/turn`. Cursor/agent: `python -m facio_api.mcp` (stdio; founding desk; same 16 tools as talk).

## Docker (preferred)

From the repo root:

```bash
cp apps/api/.env.example .env
docker compose up --build
```

Simulator talks to `http://127.0.0.1:8000`. Default mode is `scripted` (goldens, no paid key).

Live model — pick the model in `.env`; only the matching key is required:

```bash
# .env
FACIO_TALK_MODE=live
FACIO_MODEL_NAME=haiku
FACIO_ANTHROPIC_API_KEY=sk-ant-...
# FACIO_OPENAI_API_KEY=           # optional, unused while the model is Haiku

docker compose up --build
```

`FACIO_MODEL_NAME=gpt-4o-mini` (or `gpt`) uses `FACIO_OPENAI_API_KEY`. `haiku` / `claude-haiku-4-5` uses `FACIO_ANTHROPIC_API_KEY`.

## Local venv

```bash
cd apps/api
python3 -m venv .venv
source .venv/bin/activate
pip install -e ../../packages/domain -e ".[dev]"
cp .env.example .env
fastapi dev
# eval: pytest            # live skipped
#       pytest -m live    # vendor; needs the key for FACIO_MODEL_NAME
```
