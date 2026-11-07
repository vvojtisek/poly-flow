#!/usr/bin/env bash
# Run the browser E2E suite against a fresh Compose stack.
# Usage: scripts/e2e.sh [extra docker compose args]   (needs: npm ci + playwright browsers in frontend/)
set -euo pipefail
cd "$(dirname "$0")/.."
compose=(docker compose "$@")
# docker-compose.yml publishes the frontend on host port 3001.
FRONTEND=${E2E_BASE_URL:-http://localhost:3001}
export E2E_BASE_URL=$FRONTEND

cleanup() {
  status=$?
  [ "$status" -ne 0 ] && "${compose[@]}" logs --no-color --tail=200 || true
  "${compose[@]}" down -v --remove-orphans >/dev/null 2>&1 || true
  exit "$status"
}
trap cleanup EXIT

"${compose[@]}" up -d --build postgres redis migrate backend worker frontend
for _ in $(seq 1 100); do
  curl -sf $FRONTEND/api/v1/setup >/dev/null && break
  sleep 3
done
"${compose[@]}" exec -T backend sh -c 'python -m app.cli seed-lexicon data/lexicon/*.csv && python -m app.cli seed-scenes data/scenes/*.json && python -m app.cli seed-grammar data/grammar/*.json'
# The dev server compiles pages on first hit; warm them so test timeouts measure the app.
for page in / /setup /login /profiles /lesson /check; do
  curl -s -o /dev/null --max-time 180 "$FRONTEND$page"
done
(cd frontend && npx playwright test)
