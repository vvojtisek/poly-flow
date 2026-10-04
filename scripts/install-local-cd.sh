#!/usr/bin/bash
set -Eeuo pipefail

repo_root=$(cd -- "$(/usr/bin/dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
user_bin="$HOME/.local/bin"
user_systemd="$HOME/.config/systemd/user"
user_config="$HOME/.config/polyflow"

[[ -f "$repo_root/.env" ]] || {
  printf 'Copy .env.example to .env and set POSTGRES_PASSWORD before installing.\n' >&2
  exit 1
}

install -Dm700 "$repo_root/scripts/deploy-main.sh" "$user_bin/polyflow-deploy-main"
install -Dm644 "$repo_root/deploy/systemd/polyflow-local-cd.service" \
  "$user_systemd/polyflow-local-cd.service"
install -Dm644 "$repo_root/deploy/systemd/polyflow-local-cd.timer" \
  "$user_systemd/polyflow-local-cd.timer"
install -Dm600 "$repo_root/docker-compose.local.yml" "$user_config/compose.override.yaml"

systemctl --user daemon-reload
systemctl --user enable --now polyflow-local-cd.timer
printf 'Enabled polyflow-local-cd.timer; it checks origin/main once per minute.\n'
printf 'The timer only deploys a clean local main checkout and never stops unrelated containers.\n'
