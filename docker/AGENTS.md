# Container and Compose instructions

Read the repository `AGENTS.md` before editing. Compose and Dockerfiles define the self-hosted runtime for the API, ARQ worker, web app, PostgreSQL, Redis, and optional audio services.

- Keep runtime containers non-root and expose only the ports needed by the host. Keep PostgreSQL, Redis, and internal model APIs on private Compose networks unless a documented local-development need requires a loopback-only binding.
- Preserve health checks and startup dependency ordering for database migrations, API, and workers. A health check does not replace runtime retry handling.
- Avoid development bind mounts and development targets in production Compose. Keep secrets in environment/secret management, never in Docker build arguments or image layers.
- Pin image and model versions for reproducible deployments; document downloads, checksums, storage volumes, and hardware assumptions for large speech models.
- Check Compose interpolation with `docker compose config -q` and build only the affected image targets after changes. Review volume migration and rollback impact before renaming persisted service/volume paths.

