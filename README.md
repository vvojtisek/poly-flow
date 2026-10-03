# PolyFlow

A self-hosted language-learning platform (DE / FR / IT from Czech) for a family homelab.
Modular monolith: FastAPI + ARQ worker + PostgreSQL 16 + Redis + Next.js PWA, with local Piper TTS and faster-whisper STT.

Status: **Phase 1 scaffold** (schema, migrations, Compose stack, lexicon/blacklist seeding, health endpoints).

The [LinguaCore implementation plan](docs/IMPLEMENTATION_PLAN.md) maps the updated family-platform specification to this scaffold, including the vocabulary milestones (100 → 5000, plus the voluntary 6000+ extension), delivery phases, and acceptance criteria. The code and schema below still describe the current implementation.

## Layout

```
backend/
  app/
    api/          HTTP routers (health)
    core/         settings, JSON logging, request middleware
    db/           declarative base, async engine/session, shared PG enum types
    domain/       enums and domain constants (frequency bands, decay window, grammar gate)
    models/       SQLAlchemy models
    services/     domain services (Phase 2+)
    workers/      ARQ worker settings + entrypoint
    cli.py        seeding CLI
  alembic/        migrations
  data/           seed CSVs (see data/README.md)
  tests/
frontend/         Next.js App Router PWA (Tailwind v4, lucide-react), cs-CZ UI strings in lib/i18n
docker/
  backend/        multi-stage image; targets `api` and `worker`
  frontend/       targets `dev` (hot reload) and `runner` (standalone prod)
  piper/          Piper TTS HTTP server, voices downloaded into a volume on first start
  whisper/        faster-whisper HTTP API with word-level probabilities
docker-compose.yml
```

## Run

```sh
cp .env.example .env            # set POSTGRES_PASSWORD
docker compose up --build       # postgres, redis, migrate, backend, worker, frontend
docker compose --profile audio up --build   # + piper, whisper (first start downloads models)

# seed
docker compose run --rm backend python -m app.cli seed-lexicon data/lexicon/de.sample.csv data/lexicon/fr.sample.csv data/lexicon/it.sample.csv
docker compose run --rm backend python -m app.cli seed-blacklist data/blacklist/default.csv
```

Smoke test of the core stack from scratch (also runs in CI): `scripts/compose-smoke.sh`.

The browser talks only to the frontend origin; Next.js proxies `/api/*` and `/readyz` to the backend
(`BACKEND_URL`, resolved at build time for the production `runner` image).

- API: http://localhost:8000 (`/healthz` liveness, `/readyz` checks Postgres + Redis, 503 when unready; OpenAPI at `/docs`)
- Frontend: http://localhost:3000

Behind a registry mirror, pass `--build-arg PYTHON_IMAGE=...` / `NODE_IMAGE=...`.

## Local backend development

```sh
cd backend
uv sync --extra dev
uv run pytest                      # DB tests need POLYFLOW_TEST_DATABASE_URL (disposable DB)
uv run ruff check . && uv run ruff format --check .
POLYFLOW_DATABASE_URL=postgresql+asyncpg://... uv run alembic upgrade head
uv run alembic revision --autogenerate -m "..."   # then review; `alembic check` must be clean
```

All settings are env vars prefixed `POLYFLOW_` (see `app/core/config.py`).

## Schema (Phase 1)

| table | purpose |
|---|---|
| `users` | profiles, `is_child`, JSONB `settings`, XP / coins / streak stats |
| `lexicon_items` | lemma, language, frequency rank (+ derived milestone band), Czech gloss, IPA, CEFR |
| `user_word_progress` | `NEW/LEARNING/MASTERED` state, `passive_known` / `active_known`, phonetic & orthography scores (NULL = never measured), review / error-free / decay timestamps |
| `content_blacklist` | keyword / regex patterns per language (NULL = all) and category, for child profiles |
| `daily_stories` | per-user, per-language, per-day generated story with comprehension questions and provenance |

## Vocabulary progression

Defined in `backend/app/domain/progression.py`, served at `GET /api/v1/progression/milestones`.

| words (frequency rank) | milestone |
|---|---|
| 100 | core |
| 500 | basics |
| 1,000 | A2 (grammar lessons unlock) |
| 2,500 | B1 |
| 4,000 | B2 threshold |
| 5,000 | full B2: end of the curriculum |
| 6,000+ | voluntary extension, passive-recognition focus, no CEFR claim |

Past 5,000 the learner may keep training, but the app states plainly that advancing to C1 comes from
real use of the language (people, media, culture), not from more drills. CEFR tags are heuristics:
CEFR describes communicative ability, and word count is only one component of it.

Logs are one JSON object per line on stdout, with `request_id` propagated from/to the `X-Request-ID` header.
