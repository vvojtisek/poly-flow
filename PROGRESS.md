# PROGRESS: desktop-first Czech → German platform

Checkpoint file for the desktop / German / adaptive-engine track started 2026-11-05 (request by
Vlad). Read this file, `git log` and `git status` before resuming work. Each milestone is
committed separately and this file is updated with every commit.

Branch: `claude/project-thread-l6h5lh` (base `main` at `6444ccf`, version `1.0.0-alpha.4`).

## Audit (2026-11-05)

What already exists and is kept (see `README.md`, `docs/IMPLEMENTATION_PLAN.md`, `AGENTS.md`):

| Area | Shipped on `main` | Gap for this track |
|---|---|---|
| Stack | FastAPI + SQLAlchemy/Alembic (13 migrations) + Postgres, ARQ/Redis worker, Next.js 16 PWA, Docker Compose, CI | none; kept as is |
| Profiles | admin + learner roles, child = content filter, PIN/password, per-profile settings (theme, interests, voice, speed) | none |
| Languages | DE, FR, IT, EN from Czech; separate progress per profile and language | language-specific rules are spread over several modules (no single language pack) |
| Vocabulary | lexicon with provenance; DE/FR/IT core 100, EN 1-1000; frequency reference lists (EN) | **German stops at 100 words** |
| Lessons | Lekce (scene first, ungraded, hints, retries) vs Ověření (one try, only evidence); policy v3 | no remediation of past mistakes inside lessons |
| SRS | per-word passive/active knowledge, review intervals 1-30 days, idempotent 30-day decay | no per-grammar-rule SRS |
| Mistakes | every attempt is a `learning_events` row (answer, verdict, evidence flag) | not analysed: no error categories, no weak-spot view |
| Placement / exams | adaptive placement test, vocabulary level exams A1-B2, badges | none |
| Audio | Piper TTS (cached), Whisper STT answers for recall tasks | none |
| Grammar | only a `grammar_unlocks` table (gate: 1000 known words) | **no grammar content, exercises, or UI** |
| AI | `daily_stories` table with `llm_provider` columns, unused | **no LLM adapter, tutor, or generated stories** |
| Desktop UX | mobile-first, clickable; no keyboard shortcuts | **no hotkeys, umlaut input, split pane** |

Decisions that this track must respect (project memory, AGENTS.md): learning vs testing stay
separate (only checks are evidence); child profiles get filtered content and must not receive
unvalidated generated text; generated or drafted content is stored as unreviewed; no cloud
fallback without an explicit setting; every PR bumps `1.0.0-alpha.N`.

Change of direction (Vlad, 2026-11-05): no virtual currency, streaks, leaderboards or competition.
Plan phase P6 (XP, coins, streaks, mini-games) is dropped; progress shows mastery only.

## Open questions for Vlad (asked 2026-11-05)

1. Push the branch and open a draft PR, or keep commits local only? (cloud sandbox: unpushed
   commits are lost when the session ends). Until answered: local commits only.
2. Grammar lessons open from A1, or locked until 1000 known words (current AGENTS.md rule)?
   Until answered: implemented behind one function (`app.domain.grammar.grammar_open`), default
   open from A1 as recommended.
3. Which local LLM runtime/model for the tutor and stories? Until answered: an
   OpenAI-compatible adapter (Ollama / llama.cpp), disabled unless `POLYFLOW_LLM_URL` is set,
   with deterministic Czech explanations from the curriculum when it is off.

## Milestones

Status: `[x]` done and committed, `[~]` in progress, `[ ]` not started.

- [x] **M0 Audit and roadmap**: this file.
- [x] **M1 Desktop ergonomics** (frontend): `Enter` submits / continues, digit keys pick answer
      options using physical key codes (works on the Czech layout, where the top row types
      `+ěščřžýáíé`), quick German character bar (`ä ö ü ß` + capitals) with `Alt+a/o/u/s`
      shortcuts, `?`/`H` for hint, `Esc` leaves to the overview, a shortcut legend, wider layout and a
      split pane (scene and word notes beside the practice) on wide screens; mobile layout unchanged.
- [ ] **M2 Mistake engine for words**: classify each wrong answer (wrong article/gender, missing
      umlaut/diacritics, capitalisation, misspelling, wrong meaning), keep it on the event,
      weak-spot query per profile and language, inject recently missed words as ungraded
      remediation practice at the start of the next Lekce, weak-spot overview in the UI.
- [ ] **M3 Grammar module**: content-pack format (`backend/data/grammar/*.json`) with provenance and
      review status, tables for rules, exercises, per-rule progress and attempts (migration
      0014), German A1-B2 skill tree with Czech explanations; Lekce for a rule (notes in a split
      pane + ungraded practice with retries and explanations) and Ověření gramatiky (one try,
      per-rule SRS with the same intervals and idempotent decay); mistakes feed the rule's review.
- [ ] **M4 Exercise types**: grammar exercises `choice` (der/die/das, cases, prepositions),
      `gap` (typed conjugation/ending), `order` (sentence building from tiles) and `translate`
      (cs → de and de → cs with accepted variants), all graded on the server.
- [ ] **M5 AI tutor**: LLM adapter (OpenAI-compatible chat completions, local by default, timeout,
      provider/model recorded), "Proč?" explanation in Czech after any answered task: always the
      curriculum's deterministic explanation, optionally expanded by the model; output validated
      (length, language, blacklist) and never shown to child profiles unvalidated; never reveals a
      pending check answer.
- [ ] **M6 Generated stories and dialogues**: short story/dialogue from the learner's known words
      plus 3-5 targets, structured output, vocabulary-coverage and safety validation, stored with
      provenance, reader UI with TTS and comprehension questions.
- [ ] **M7 German vocabulary 101-1000**: drafted lexicon rows (gloss, gender, plural-free lemma,
      example) marked `claude-draft` / unreviewed, plus scenes for the new words.
- [ ] **M8 Language-pack registry**: one module per target language (articles, spelling
      variants, special characters, voice, data files) so `cs → es` is configuration + data.
- [ ] **M9 Verification and release bump**: backend tests, ruff, alembic check, frontend
      typecheck/build, Playwright run on localhost, version `1.0.0-alpha.5`.

## Log

- 2026-11-05: M1 done. `lib/keyboard.ts` (data-hotkey listener, physical digit keys, Alt+letter characters), `AnswerInput`, key badges and legend on lg screens, scene side pane in Lekce. Playwright: mobile spec + new keyboard-only desktop spec pass on localhost.

- 2026-11-05: audit done; baseline `uv run pytest` = 283 passed, 1 skipped (local Postgres 16).
