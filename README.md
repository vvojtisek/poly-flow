# PolyFlow

A self-hosted language-learning platform (DE / FR / IT from Czech) for a family homelab.
Modular monolith: FastAPI + ARQ worker + PostgreSQL 16 + Redis + Next.js PWA, with local Piper TTS and faster-whisper STT.

Status: **first usable version** (implementation plan P0–P2): family profiles with parent-managed child
profiles, the first 100 curated words per language, server-graded lessons with spaced review and decay,
persistent progress per profile and language.

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
docker compose run --rm backend sh -c 'python -m app.cli seed-lexicon data/lexicon/*.csv && python -m app.cli seed-scenes data/scenes/*.json'
docker compose run --rm backend python -m app.cli seed-blacklist data/blacklist/default.csv
```

Open http://localhost:3000. The first visit runs **first-run setup**, which creates the parent account
(there is no open registration afterwards). The parent then adds profiles under *Rodina*:

- **adult** profiles sign in with their own password;
- **child** profiles get an optional PIN. Without a PIN, the parent opens the child profile from their own
  session (*Předat zařízení*); returning to the parent account requires the parent's password.

Smoke test of the core stack from scratch (also runs in CI): `scripts/compose-smoke.sh`.
Browser E2E (setup → child → lesson → reload → progress) against a fresh stack: `scripts/e2e.sh`
(run `npm ci && npx playwright install chromium` in `frontend/` first).

Serve over HTTPS in any shared deployment and set `POLYFLOW_COOKIE_SECURE=true`; the session cookie is
HttpOnly and SameSite=Lax, and every write needs the per-session CSRF token.

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

## Schema

| table | purpose |
|---|---|
| `users` | profiles: role (parent = admin), `is_child`, password / optional child PIN (argon2), timezone, JSONB `settings`, XP / coins / streak stats |
| `auth_sessions` | server-side sessions (token digests only): who signed in and which profile is currently in use |
| `lexicon_items` | lemma, language, frequency rank (+ derived milestone band), Czech gloss, IPA, CEFR, provenance (`source`, `license`, `revision`) |
| `user_word_progress` | `NEW/LEARNING/MASTERED` state, `passive_known` / `active_known`, phonetic & orthography scores (NULL = never measured), last seen / reviewed / error-free / decay timestamps, `next_review_at`, review streak |
| `learning_sessions`, `learning_tasks` | server-issued lessons and their tasks; at most one open lesson per profile and language |
| `learning_events` | every graded attempt (idempotency key, verdict, hint, evidence flag, policy version); progress is aggregated from these |
| `grammar_unlocks` | persistent grammar unlock per profile and language (decay never re-locks) |
| `content_blacklist` | keyword / regex patterns per language (NULL = all) and category, for child profiles |
| `daily_stories` | per-user, per-language, per-day generated story with comprehension questions and provenance |

## Learning rules (policy `v1`)

Defined in `backend/app/domain/learning_policy.py`; pilot values, versioned with every event and progress row.

- A lesson shows due reviews first, then up to 4 new words: each new word is first **recognised**
  (pick the Czech meaning), later in the same lesson **produced** (write it).
- Only a **first-try, hint-free** correct answer counts as evidence. Hints and retries are unlimited
  but do not count; the word comes back soon instead.
- `passive_known`: 3 evidences on ≥ 2 different days (writing the word also proves recognising it).
  `active_known`: 3 written evidences on ≥ 2 days. `MASTERED`: both, plus a successful check ≥ 7 days later.
- Spelling is checked per language: accepted variants (`ss` for `ß`, `ae`/`oe`/`ue` for umlauts, `oe` for `œ`)
  count with a note; a lowercase German noun or missing diacritics are explained and do not count.
- Review intervals after consecutive successes: 1, 2, 4, 7, 14, 30 days. After **30 days** without a verified
  error-free use, the nightly worker job (02:30 local) puts the word back into priority review and demotes
  `MASTERED` to `LEARNING`; measured scores are kept and effective retention is derived on read.
- Grammar mini-lessons unlock per language once 1000 lemmas of the first 1000 ranks are known (P5 builds them).
- Pronunciation is not scored: `phonetic_score` stays NULL until a validated measurement exists (plan P3).

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
