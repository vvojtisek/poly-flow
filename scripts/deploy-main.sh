#!/usr/bin/bash
set -Eeuo pipefail

say() {
  printf 'polyflow-local-cd: %s\n' "$*"
}

fail() {
  say "ERROR: $*" >&2
  exit 1
}

repo_root=${POLYFLOW_REPO_ROOT:?POLYFLOW_REPO_ROOT must point to the PolyFlow checkout}
override_file=${POLYFLOW_COMPOSE_OVERRIDE:?POLYFLOW_COMPOSE_OVERRIDE must point to the local Compose override}
state_file=${POLYFLOW_DEPLOY_STATE:?POLYFLOW_DEPLOY_STATE must point to the deployed-commit marker}

[[ -d "$repo_root/.git" || -f "$repo_root/.git" ]] || fail "not a Git checkout: $repo_root"
[[ -f "$repo_root/.env" ]] || fail "missing local .env; copy .env.example and configure it first"
[[ -f "$override_file" ]] || fail "missing local Compose override: $override_file"

branch=$(/usr/bin/git -C "$repo_root" branch --show-current)
[[ "$branch" == main ]] || {
  say "skipping: checkout is on '$branch'; automatic deploy only follows local main"
  exit 0
}

changes=$(/usr/bin/git -C "$repo_root" status --porcelain --untracked-files=normal)
[[ -z "$changes" ]] || {
  say "skipping: the main checkout has local changes; refusing to overwrite them"
  exit 0
}

/usr/bin/git -C "$repo_root" fetch --quiet origin +refs/heads/main:refs/remotes/origin/main
local_sha=$(/usr/bin/git -C "$repo_root" rev-parse HEAD)
remote_sha=$(/usr/bin/git -C "$repo_root" rev-parse refs/remotes/origin/main)

if [[ "$local_sha" != "$remote_sha" ]]; then
  /usr/bin/git -C "$repo_root" merge-base --is-ancestor "$local_sha" "$remote_sha" \
    || fail "local main diverges from origin/main; refusing to reset or merge"
  say "fast-forwarding main to ${remote_sha:0:12}"
  /usr/bin/git -C "$repo_root" merge --ff-only "$remote_sha"
  local_sha=$remote_sha
fi

mkdir -p "$(/usr/bin/dirname "$state_file")"
deployed_sha=""
if [[ -f "$state_file" ]]; then
  deployed_sha=$(<"$state_file")
fi
if [[ "$local_sha" == "$deployed_sha" ]]; then
  exit 0
fi

compose=(/usr/bin/docker compose --project-directory "$repo_root" \
  -f "$repo_root/docker-compose.yml" -f "$override_file")
"${compose[@]}" config -q
say "building and starting PolyFlow at ${local_sha:0:12}"
"${compose[@]}" up -d --build

# Keep packaged curriculum and safety rules in sync with the deployed commit.
"${compose[@]}" run --rm --no-deps backend sh -c \
  'python -m app.cli seed-lexicon data/lexicon/*.csv'
"${compose[@]}" run --rm --no-deps backend \
  python -m app.cli seed-blacklist data/blacklist/default.csv

for url in http://127.0.0.1:8000/readyz http://127.0.0.1:3000/; do
  ready=false
  for _ in {1..90}; do
    if /usr/bin/curl --silent --show-error --fail --max-time 3 "$url" >/dev/null; then
      ready=true
      break
    fi
    /usr/bin/sleep 1
  done
  [[ "$ready" == true ]] || fail "health check timed out: $url"
  say "healthy: $url"
done

tmp_state="${state_file}.tmp.$$"
printf '%s\n' "$local_sha" > "$tmp_state"
chmod 600 "$tmp_state"
mv -f "$tmp_state" "$state_file"
say "deployment complete at ${local_sha:0:12}"
