# Backend instructions

Read the repository `AGENTS.md` first. The backend owns FastAPI transport, domain rules, async persistence, migrations, and ARQ processing.

- Keep domain rules in `app/domain/`; keep HTTP schemas/routes in `app/api/`; orchestrate application work in `app/services/`.
- Use the async SQLAlchemy session patterns in `app/db/`. Do not block the event loop in API requests or worker jobs.
- Add a new Alembic revision for schema changes. Review generated SQL and constraints, preserve existing learner data, and verify migration state against the models. Do not rewrite an applied migration to change history.
- Validate API input and enforce profile ownership/child permissions on the server. Keep API response schemas explicit and document behavior through FastAPI/OpenAPI.
- ARQ jobs may run again after interruption. Make writes transactional and jobs idempotent; give per-profile/language/day content runs stable uniqueness keys.
- Do not treat Whisper transcription probability as a pronunciation measurement. Leave unavailable measurements unset and preserve their meaning in API contracts.
- For backend changes, run focused pytest and Ruff checks. Use Alembic upgrade/check and representative-data checks for schema changes.

