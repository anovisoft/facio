#!/usr/bin/env bash
# Run client-service pytest suite against local Postgres (fasio_test).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE="$ROOT/apps/backend-py3/client-service"
DATABASE_URL="${DATABASE_URL:-postgresql+asyncpg://fasio:fasio@localhost:5435/fasio_test}"

cd "$ROOT"

echo "==> Ensuring fasio-postgres is up"
docker compose up -d fasio-postgres

echo "==> Waiting for Postgres"
for _ in $(seq 1 30); do
  if docker exec fasio-postgres pg_isready -U fasio -d fasio >/dev/null 2>&1; then
    break
  fi
  sleep 1
done
docker exec fasio-postgres pg_isready -U fasio -d fasio

echo "==> Ensuring fasio_test database exists"
docker exec fasio-postgres psql -U fasio -d fasio -tc \
  "SELECT 1 FROM pg_database WHERE datname='fasio_test'" | grep -q 1 \
  || docker exec fasio-postgres psql -U fasio -d fasio -c "CREATE DATABASE fasio_test;"

cd "$SERVICE"

if command -v uv >/dev/null 2>&1; then
  UV=(uv)
elif [[ -x "$HOME/.local/bin/uv" ]]; then
  UV=("$HOME/.local/bin/uv")
else
  echo "uv not found; install from https://docs.astral.sh/uv/" >&2
  exit 1
fi

echo "==> Syncing dev deps"
"${UV[@]}" sync --group dev

echo "==> Running pytest"
export DATABASE_URL
export LOG_DIR="${LOG_DIR:-}"
export ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-}"
"${UV[@]}" run pytest "$@"
