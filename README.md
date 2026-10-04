# PolyFlow

A self-hosted language-learning platform (DE / FR / IT / EN from Czech) for a family homelab.
Modular monolith: FastAPI + ARQ worker + PostgreSQL 16 + Redis + Next.js PWA, with local Piper TTS and faster-whisper STT.

Status: **first usable version** (implementation plan P0–P2): family profiles (an admin grants access,
child profiles get an age-appropriate content filter), the first 100 curated words per language, server-graded lessons with spaced review and decay,
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
docker compose --profile audio up --build   # + piper, whisper (first start fetches pinned models)

# seed
docker compose run --rm backend sh -c 'python -m app.cli seed-lexicon data/lexicon/*.csv && python -m app.cli seed-scenes data/scenes/*.json'
docker compose run --rm backend python -m app.cli seed-blacklist data/blacklist/default.csv
docker compose run --rm backend python -m app.cli seed-lemmas data/frequency/en_GB.lemmas.csv data/frequency/en_US.lemmas.csv  # frequency reference, no glosses
```

Open http://localhost:3000. The first visit runs **first-run setup**, which creates the admin account
(there is no open registration afterwards). The admin then adds profiles under *Rodina*. Roles:

- **admin** grants access (creates profiles, resets a password or PIN, deactivates) and edits shared
  content (`GET/PATCH /api/v1/lexicon`). The admin does not decide what others learn: language, daily goal
  and audio settings belong to each profile.
- **every profile** signs in on its own with a password or a PIN (admins: password).
- **child** is a content filter, not a restriction: lexicon items with `content_flags`
  (`sexual`, `profanity`, `violence`) never reach a child profile, as new words, reviews or answer options.
  The admin can switch the filter on or off per profile. On a shared tablet the admin can also open a child
  profile from their own session (*Předat zařízení*); returning to the admin account requires the admin's
  password.

### Audio (Piper TTS, Whisper STT)

Voices and STT models are pinned by Hugging Face commit and sha256 in `docker/models/models.lock.json`
(generated from `models.spec.json` by `python3 scripts/models.py lock --missing`, which resolves only new entries). The one-shot `models` service
fetches what is missing into the volumes and verifies it; with complete volumes it needs no network, and
Piper and Whisper themselves never download anything. `python3 scripts/models.py verify --dest DIR`
re-hashes everything.

- `WHISPER_MODEL` (`tiny`, `base`, `small`, `medium`, `large-v3-turbo`; default `small`) selects the STT model.
- On an NVIDIA GPU add `-f docker-compose.gpu.yml` (CUDA 12, float16); without it Whisper runs on CPU (int8).
- Uploads are limited (`WHISPER_MAX_SECONDS`, `WHISPER_MAX_UPLOAD_BYTES`), decoded in memory, never stored.
- Lessons play scene lines, new words and task words through Piper. The backend serves only text a
  lesson already shows (a pending "write the word" task stays silent), and caches each clip in the
  `audiocache` volume, keyed by text, voice and the voice's configuration. Deleting the volume only
  costs re-synthesis. Without the `audio` profile the play buttons report that sound is unavailable
  and the lesson works as text.
- A "write the word" task can also be answered by voice. Whisper transcribes the recording,
  which is then discarded. A transcript that is exactly the word, with every word at least
  `spoken_min_confidence` sure (policy v3, provisional 0.5), counts like a typed answer.
  Anything else is "not understood" and counts neither way. Browsers allow the microphone only
  over HTTPS or on `localhost`, so phones on the home network need HTTPS (plan P7).
- `scripts/bench_audio.py` measures latency on the target machine; see [docs/HARDWARE.md](docs/HARDWARE.md).
  The `audio` CI workflow runs it in smoke mode with `tiny` when audio files change and weekly.

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

## Versions and releases

The current state is **pre-release 1.0**: version `1.0.0-alpha.1` ([SemVer](https://semver.org) pre-release).
`/VERSION` is canonical; `scripts/set-version.sh <version>` updates every copy (backend package,
`pyproject.toml`/`uv.lock` in PEP 440 spelling, `frontend/package.json`), and a backend test fails if they drift.

Every page shows the running build in its header, right under the logout button (on the login page,
under the form), and `GET /version` returns the same for the backend:

| Build | Shown |
|---|---|
| release (`1.0.0`) | `1.0.0 · abc1234` |
| pre-release (`1.0.0-alpha.1`) | `1.0.0-alpha.1 · main · abc1234` + badge *předběžná verze* |
| dev server (`next dev`, the Compose default) | adds the branch and a *vývoj* badge |

Commit, branch and build time are baked in when images are built. Run
`eval "$(scripts/build-info.sh)"` before `docker compose up --build`; without it they read `unknown`.
The local CD timer (`scripts/deploy-main.sh`) does this itself.
A local `npm run dev` asks git directly. A `-dirty` suffix means the build had uncommitted changes.

Branching (see `AGENTS.md`): until 1.0 ships, work lands on `main` through short-lived branches.
At release, `main` is tagged `v1.0.0` and from then on tracks released code only; ongoing development
moves to a development branch and reaches `main` when the next version is released and tagged.

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

## Agent workflow

Read [AGENTS.md](AGENTS.md) and the scoped `AGENTS.md` for the area you change. It is the single source of rules for both Codex and Claude Code: `CLAUDE.md` files import the matching `AGENTS.md`. Codex roles and the model router live under `.codex/`; Claude subagents and the model-router skill live under `.claude/`. The [implementation plan](docs/IMPLEMENTATION_PLAN.md) describes planned features, while the source code remains authoritative for shipped behavior.

## Schema

| table | purpose |
|---|---|
| `users` | profiles: role (admin / learner), `is_child` (content filter), one credential: password or PIN (argon2), timezone, JSONB `settings`, XP / coins / streak stats |
| `auth_sessions` | server-side sessions (token digests only): who signed in and which profile is currently in use |
| `lexicon_items` | lemma, language, frequency rank (+ derived milestone band), Czech gloss, IPA, CEFR, `content_flags` (child filter), provenance (`source`, `license`, `revision`) |
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
