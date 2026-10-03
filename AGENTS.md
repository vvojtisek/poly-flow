# PolyFlow agent guide

## Purpose

PolyFlow (product plan: LinguaCore) is a self-hosted Czech-language learning platform for German, French, and Italian. Work should preserve:

- accurate, reviewed language-learning content;
- family and child account privacy and safety;
- clear boundaries between API, domain logic, persistence, workers, and UI;
- reproducible local and production deployment;
- small changes with verification appropriate to the risk.

The current repository is an early scaffold. Read `README.md` and `docs/IMPLEMENTATION_PLAN.md` before broad or cross-cutting changes. Read `backend/data/README.md` before importing or changing lexicon/blacklist data. Inspect the implementation as well as its plans; plans describe intended behavior, not necessarily shipped code.

Explicit user instructions take precedence over these defaults. If current code, this guide, the implementation plan, or an accepted decision disagree in a material way, surface the conflict before choosing a data-destructive or compatibility-breaking interpretation.

## Product invariants

- Teach DE/FR/IT from Czech. Keep learner-facing UI copy in the Czech localization table and provide separate progress per learner and language.
- The requested frequency milestones are 100, 500, 1000, 1500, 2000, and 2500 lemmas per language. Vocabulary rank alone does not establish a CEFR communication level.
- Passive recognition and active production are separate knowledge states. An unmeasured score stays unknown; do not silently turn absent evidence into zero or full mastery.
- More than 30 days without error-free use schedules a word for review. Repeated decay jobs must be idempotent and must not compound a score decrease on each run.
- The grammar module unlocks when the learner masters the first 1000-word block in that language. Decay does not revoke an earned unlock. Practice itself has no lives, energy limits, or paid gates.
- Child-facing generated text, questions, dialogue, and audio must pass the active safety checks before publication or playback. Source text and learner input are untrusted data, never privileged model instructions.
- Speech recognition confidence is not a calibrated pronunciation score. Keep transcription confidence, transcription correctness, and pronunciation assessment distinct.
- Record source, licensing, and review status for imported curriculum data. Do not present generated or approximate translations as reviewed fact.

## Architecture and ownership

- `backend/app/api/` owns HTTP routing and transport schemas.
- `backend/app/domain/` owns deterministic learning rules and domain types.
- `backend/app/services/` owns application use cases and orchestration.
- `backend/app/db/`, `backend/app/models/`, and `backend/alembic/` own persistence and schema migrations.
- `backend/app/workers/` owns ARQ background processing; tasks must be retry-safe and idempotent.
- `backend/data/` contains source datasets and their import documentation.
- `frontend/app/`, `frontend/components/`, `frontend/hooks/`, and `frontend/lib/` own the Next.js UI, browser state, API calls, and Czech copy.
- `docker/`, `docker-compose.yml`, and `.github/workflows/` own service images, deployment composition, and CI.

Keep domain rules out of React components and HTTP handlers. Keep child authorization and content safety enforcement on the server. Use existing SQLAlchemy/Alembic, FastAPI, ARQ/Redis, and Next.js patterns; propose an ADR before replacing a framework, database, job system, API style, or model-provider trust boundary.

## Implementation workflow

Before editing, inspect the applicable files, tests, migrations, `docs/IMPLEMENTATION_PLAN.md`, and any nested `AGENTS.md`. Identify current behavior and affected API/data contracts. Keep the change within the requested scope and make one logical change per branch.

During work, preserve migration history, existing learner progress, structured logging, request IDs, and offline/self-hosted operation. Make worker jobs safe to retry. Do not add a cloud fallback that can send learner data externally without an explicit setting. Do not include private audio, child profile details, credentials, or complete learner text in logs.

For vocabulary imports, validate uniqueness and schema, retain provenance and license details, and never replace an existing learner's progress. For generated content, validate the structured output, language level, target words, comprehension answers, and child-safety policy before storing it as publishable.

## Verification

Run the narrowest meaningful checks for changed code and the relevant project checks before declaring an implementation complete. Never report a check as passing unless it ran successfully. Inspect the final diff for generated files, secrets, unrelated edits, and migration/data compatibility.

Backend commands from `backend/`:

```sh
uv sync --frozen --extra dev
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run alembic upgrade head
uv run alembic check
```

Frontend commands from `frontend/`:

```sh
npm ci
npm run typecheck
npm run build
```

Compose and image checks from the repository root:

```sh
docker compose config -q
docker build -f docker/backend/Dockerfile --target api backend
docker build -f docker/backend/Dockerfile --target worker backend
docker build -f docker/frontend/Dockerfile --target runner frontend
```

For schema changes, review the migration and verify upgrade/downgrade behavior against representative data. For worker changes, check duplicate delivery, interruption, and retry behavior. For API or UI flows, verify the user-visible success, loading, empty, and failure states that are in scope.

## Security and privacy

Never commit `.env`, credentials, tokens, private keys, or real user recordings. `.env.example` must contain placeholders only. Validate all external input at the API boundary. Enforce authorization for every profile ID server-side. Limit upload sizes and durations; use temporary storage and remove audio according to the configured retention policy.

Treat feed HTML, scraped content, LLM output, model output, and uploaded audio as untrusted. A regex or prompt alone is not a safety boundary. Do not expose unpublished child content or generation diagnostics through learner APIs.

## Git conventions

Keep `main` releasable. Use branch prefixes `feat/`, `fix/`, `refactor/`, `docs/`, `test/`, or `chore/`. Use Conventional Commits (`<type>(<scope>): <description>`). Keep commits focused. Do not rewrite, force-push, merge, or delete another contributor's work unless explicitly instructed.

## Codex model routing

For substantial software-engineering work, follow `.codex/skills/adaptive-model-router/SKILL.md` and the configured roles under `.codex/agents/`. Use the lowest-cost capable route and pass concrete evidence when escalating. The coordinator remains responsible for reviewing changes and reporting actual verification.

