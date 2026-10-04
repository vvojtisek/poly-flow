#!/usr/bin/env bash
# Print build provenance as shell exports; docker-compose.yml passes them into the images.
# Usage: eval "$(scripts/build-info.sh)" && docker compose up --build
# Without this, builds still work and report commit/branch as "unknown".
set -euo pipefail
cd "$(dirname "$0")/.."

sha=$(git rev-parse HEAD 2>/dev/null || echo unknown)
# CI checkouts are detached: prefer the PR head branch, then the pushed ref name.
branch=${GITHUB_HEAD_REF:-${GITHUB_REF_NAME:-$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)}}
if [ "$branch" = "HEAD" ]; then
  branch=$(git describe --tags --exact-match 2>/dev/null || echo detached)
fi
if [ "$sha" != unknown ] && [ -n "$(git status --porcelain --untracked-files=no 2>/dev/null)" ]; then
  sha="$sha-dirty"
fi

printf 'export POLYFLOW_GIT_SHA=%q\n' "$sha"
printf 'export POLYFLOW_GIT_BRANCH=%q\n' "$branch"
printf 'export POLYFLOW_BUILD_TIME=%q\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
