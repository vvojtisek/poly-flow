# Local continuous deployment

The optional user-level systemd timer checks `origin/main` every minute. After a fast-forwardable merge reaches GitHub `main`, it fast-forwards the local `main`, rebuilds the Compose services, applies database migrations through Compose, imports the versioned lexicon and child-safety blacklist, then checks backend readiness and the frontend. It records the deployed commit only after those steps succeed, so a failed deployment is retried on a later check.

## Install

From the PolyFlow checkout, with a clean local `main` branch preferred:

```sh
cp .env.example .env
# Set a private POSTGRES_PASSWORD in .env.
chmod 600 .env
scripts/install-local-cd.sh
```

If PolyFlow is already running, keep its database volume. The install does not run `down -v` or stop other Compose projects. The local override uses the frontend's standalone runner image instead of a home-directory bind mount, which avoids Fedora SELinux permission failures. If installed while on a feature branch, the timer waits until the checkout returns to `main` before it deploys.

To have the user timer continue after logout and start before the next login, enable systemd lingering once with an administrator account:

```sh
sudo loginctl enable-linger "$USER"
```

Without lingering, the timer runs while the user's systemd session is active.

## Behavior and operation

- Deployment follows only `origin/main`. It does not change branches, reset, stash, or overwrite local edits. It skips if the checkout is on another branch or dirty, and stops on divergence.
- Compose uses the stable project name `polyflow` and the existing named volumes. A bind/port conflict makes the deployment fail visibly in the journal; the script does not kill or reconfigure the other process.
- Audio services remain opt-in under the `audio` Compose profile.
- Inspect the timer with `systemctl --user status polyflow-local-cd.timer` and deployment output with `journalctl --user -u polyflow-local-cd.service`.
- Deploy the current `main` immediately with `systemctl --user start polyflow-local-cd.service`.
- Pause with `systemctl --user disable --now polyflow-local-cd.timer`; resume with `systemctl --user enable --now polyflow-local-cd.timer`.
- The deploy stamps commit, branch and build time into the images (`scripts/build-info.sh`), so the GUI shows which commit is running.
- The timer runs an installed copy of `scripts/deploy-main.sh` in `~/.local/bin`. After a change to that script reaches `main`, re-run `scripts/install-local-cd.sh` to pick it up.
- The `deployed-main` marker lives under `~/.local/state/polyflow/`. If a build, migration, seed, or health check fails, the marker stays unchanged and the next poll retries.

The timer does not run application tests for each deployment. CI is responsible for validating merged changes before they reach `main`.
