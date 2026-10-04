#!/usr/bin/env bash
# Set the release version everywhere it is recorded. /VERSION is canonical.
# Usage: scripts/set-version.sh 1.0.0-alpha.2   (SemVer; pre-release tags: alpha.N, beta.N, rc.N)
set -euo pipefail
cd "$(dirname "$0")/.."

v=${1:?usage: scripts/set-version.sh <semver>}
if ! [[ $v =~ ^[0-9]+\.[0-9]+\.[0-9]+(-(alpha|beta|rc)\.[0-9]+)?$ ]]; then
  echo "not a supported version: $v (expected X.Y.Z or X.Y.Z-{alpha,beta,rc}.N)" >&2
  exit 1
fi
# PEP 440 spelling for pyproject/uv.lock: 1.0.0-alpha.1 -> 1.0.0a1, -beta.N -> bN, -rc.N -> rcN.
py=$(sed -E 's/-alpha\./a/; s/-beta\./b/; s/-rc\./rc/' <<<"$v")

printf '%s\n' "$v" > VERSION
sed -i -E "s/^__version__ = \".*\"/__version__ = \"$v\"/" backend/app/__init__.py
sed -i -E "0,/^version = \".*\"/s//version = \"$py\"/" backend/pyproject.toml
(cd backend && uv lock -q)
(cd frontend && npm version "$v" --no-git-tag-version --allow-same-version >/dev/null)
echo "version set to $v (python: $py)"
