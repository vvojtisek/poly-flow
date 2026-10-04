# PolyFlow agent guide

## Purpose

PolyFlow (product plan: LinguaCore) is a self-hosted Czech-language learning platform for German, French, Italian, and English. Work should preserve:

- accurate, reviewed language-learning content;
- family privacy and age-appropriate content for child profiles;
- clear boundaries between API, domain logic, persistence, workers, and UI;
- reproducible local and production deployment;
- small changes with verification appropriate to the risk.

The current repository is an early scaffold. Read `README.md` and `docs/IMPLEMENTATION_PLAN.md` before broad or cross-cutting changes. Read `backend/data/README.md` before importing or changing lexicon/blacklist data. Inspect the implementation as well as its plans; plans describe intended behavior, not necessarily shipped code.

Explicit user instructions take precedence over these defaults. If current code, this guide, the implementation plan, or an accepted decision disagree in a material way, surface the conflict before choosing a data-destructive or compatibility-breaking interpretation.

## Product invariants

- Teach DE/FR/IT/EN from Czech (English added 2026-10-04; British spelling and voice). Keep learner-facing UI copy in the Czech localization table and provide separate progress per learner and language.
- Frequency milestones are 100 → 500 (A1) → 1000 (A2) → 2500 (B1) → 4000 (B2 threshold) → 5000 (full B2) lemmas per language; `backend/app/domain/progression.py` is the source of truth. Above 5000 is a voluntary, passive-focused 6000+ extension with no CEFR claim. CEFR labels on milestones are indicative; vocabulary rank alone does not establish a CEFR communication level.
- Passive recognition and active production are separate knowledge states. An unmeasured score stays unknown; do not silently turn absent evidence into zero or full mastery.
- More than 30 days without error-free use schedules a word for review. Repeated decay jobs must be idempotent and must not compound a score decrease on each run.
- The grammar module unlocks when the learner masters the first 1000-word block in that language. Decay does not revoke an earned unlock. Practice itself has no lives, energy limits, or paid gates.
- A child profile is an age-appropriate content filter: it hides content a child would not understand or should not see at that age (sexual content, strong language, violence). It is not parental control and does not let a parent monitor or restrict the child's learning.
- The admin role grants access (creates accounts and profiles) and edits shared content such as curriculum and lexicon. It does not limit what a learner does. Each user picks their own languages; an admin does not assign them.
- Learning and testing are separate modes. Learning has no time pressure and favors correctness and understanding; timed or scored assessment belongs only to explicit testing. A lesson introduces context first (a situation, text, or dialogue) before practicing individual words; do not open a lesson with bare known/unknown flashcards.
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

Keep domain rules out of React components and HTTP handlers. Keep profile authorization and child content filtering on the server. Use existing SQLAlchemy/Alembic, FastAPI, ARQ/Redis, and Next.js patterns; propose an ADR before replacing a framework, database, job system, API style, or model-provider trust boundary.

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

## Versioning and releases

The current state is pre-release 1.0. Until the 1.0 release, work lands on `main` through short-lived branches. After the release, `main` tracks released code and ongoing development happens on a development branch. The GUI must show the app version and, for non-release builds, the branch and commit so a production build is distinguishable from a development one. Every PR bumps the version with `scripts/set-version.sh` (before 1.0: the next `1.0.0-alpha.N`), which keeps the backend and frontend in sync. If `main` moved to the same or a higher version while the PR was open, merge `main` and bump again past it.

## Git conventions

Keep `main` releasable. Use branch prefixes `feat/`, `fix/`, `refactor/`, `docs/`, `test/`, or `chore/`. Use Conventional Commits (`<type>(<scope>): <description>`). Keep commits focused. Do not rewrite, force-push, merge, or delete another contributor's work unless explicitly instructed.

## Model routing

This file is shared by Codex and Claude Code; tool-specific routing lives next to each tool's configuration and uses the same six roles (quick worker, implementer, feature engineer, deep debugger, hard problem solver, migration architect).

- Codex: follow `.codex/skills/adaptive-model-router/SKILL.md` and the roles under `.codex/agents/`.
- Claude Code: follow `.claude/skills/model-router/SKILL.md` and the subagents under `.claude/agents/`. `CLAUDE.md` files import this guide and add nothing that contradicts it.

Use the lowest-cost capable route and pass concrete evidence when escalating. The coordinator remains responsible for reviewing changes and reporting actual verification. When changing a shared rule, edit `AGENTS.md`, not a tool-specific copy.

