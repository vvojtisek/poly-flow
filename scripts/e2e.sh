#!/usr/bin/env bash
# Run the browser E2E suite against a fresh Compose stack.
# Usage: scripts/e2e.sh [extra docker compose args]   (needs: npm ci + playwright browsers in frontend/)
set -euo pipefail
cd "$(dirname "$0")/.."
compose=(docker compose "$@")

cleanup() {
  status=$?
  [ "$status" -ne 0 ] && "${compose[@]}" logs --no-color --tail=200 || true
  "${compose[@]}" down -v --remove-orphans >/dev/null 2>&1 || true
  exit "$status"
}
trap cleanup EXIT

"${compose[@]}" up -d --build postgres redis migrate backend worker frontend
for _ in $(seq 1 100); do
  curl -sf http://localhost:3000/api/v1/setup >/dev/null && break
  sleep 3
done
"${compose[@]}" exec -T backend sh -c 'python -m app.cli seed-lexicon data/lexicon/*.csv && python -m app.cli seed-scenes data/scenes/*.json'
# The dev server compiles pages on first hit; warm them so test timeouts measure the app.
for page in / /setup /login /profiles /lesson /check; do
  curl -s -o /dev/null --max-time 180 "http://localhost:3000$page"
done
(cd frontend && npx playwright test)
