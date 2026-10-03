#!/usr/bin/env bash
# Bring up the core Compose stack from scratch and verify it serves traffic.
# Usage: scripts/compose-smoke.sh [extra docker compose args, e.g. -f override.yml]
set -euo pipefail
cd "$(dirname "$0")/.."

compose=(docker compose "$@")
BACKEND=${SMOKE_BACKEND_URL:-http://localhost:8000}
FRONTEND=${SMOKE_FRONTEND_URL:-http://localhost:3000}

cleanup() {
  status=$?
  if [ "$status" -ne 0 ]; then
    echo "::group::compose logs"
    "${compose[@]}" logs --no-color --tail=200 || true
    echo "::endgroup::"
  fi
  "${compose[@]}" down -v --remove-orphans >/dev/null 2>&1 || true
  exit "$status"
}
trap cleanup EXIT

wait_for() {  # url expected_status timeout_s
  local url=$1 want=$2 deadline=$((SECONDS + $3)) got
  until got=$(curl -s -o /dev/null -w '%{http_code}' "$url") && [ "$got" = "$want" ]; do
    if [ "$SECONDS" -ge "$deadline" ]; then
      echo "timeout: $url returned ${got:-nothing}, expected $want" >&2
      return 1
    fi
    sleep 3
  done
  echo "ok: $url -> $got"
}

"${compose[@]}" up -d --build postgres redis migrate backend worker frontend

wait_for "$BACKEND/healthz" 200 180
wait_for "$BACKEND/readyz" 200 60
wait_for "$BACKEND/api/v1/progression/milestones" 200 30
wait_for "$FRONTEND/" 200 300
wait_for "$FRONTEND/api/v1/progression/milestones" 200 60  # same-origin proxy to the API

# Seeding must work against the migrated schema.
"${compose[@]}" exec -T backend python -m app.cli seed-lexicon \
  data/lexicon/de.sample.csv data/lexicon/fr.sample.csv data/lexicon/it.sample.csv

if [ "$("${compose[@]}" ps --status running --services | grep -c '^worker$')" -ne 1 ]; then
  echo "worker is not running" >&2
  exit 1
fi
echo "compose smoke test passed"
