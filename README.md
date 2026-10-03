# PolyFlow

A self-hosted language-learning platform (DE / FR / IT from Czech) for a family homelab.
Modular monolith: FastAPI + ARQ worker + PostgreSQL 16 + Redis + Next.js PWA, with local Piper TTS and faster-whisper STT.

Status: **Phase 1 scaffold** (schema, migrations, Compose stack, lexicon/blacklist seeding, health endpoints).

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

- API: http://localhost:8000 (`/healthz` liveness, `/readyz` checks Postgres + Redis, 503 when unready; OpenAPI at `/docs`)
- Frontend: http://localhost:3000

Behind a registry mirror, pass `--build-arg PYTHON_IMAGE=...` / `NODE_IMAGE=...`.

## Local backend development

```sh
cd backend
uv sync --extra dev
uv run pytest
uv run ruff check . && uv run ruff format --check .
POLYFLOW_DATABASE_URL=postgresql+asyncpg://... uv run alembic upgrade head
uv run alembic revision --autogenerate -m "..."   # then review; `alembic check` must be clean
```

All settings are env vars prefixed `POLYFLOW_` (see `app/core/config.py`).

## Schema (Phase 1)

| table | purpose |
|---|---|
| `users` | profiles, `is_child`, JSONB `settings`, XP / coins / streak stats |
| `lexicon_items` | lemma, language, rank 1..2500 (+ derived milestone band), Czech gloss, IPA, CEFR |
| `user_word_progress` | `NEW/LEARNING/MASTERED` state, `passive_known` / `active_known`, phonetic & orthography scores (NULL = never measured), review / error-free / decay timestamps |
| `content_blacklist` | keyword / regex patterns per language (NULL = all) and category, for child profiles |
| `daily_stories` | per-user, per-language, per-day generated story with comprehension questions and provenance |

Logs are one JSON object per line on stdout, with `request_id` propagated from/to the `X-Request-ID` header.
