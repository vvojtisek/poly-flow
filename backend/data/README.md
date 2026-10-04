# Seed data

## Lexicon (`lexicon/*.csv`)

Columns: `language,rank,lemma,pos,translation_cs,ipa,cefr,gender,example`. Lines starting with `#` are comments.

| column | required | notes |
|---|---|---|
| language | yes | `de` / `fr` / `it` / `en` |
| rank | yes | >= 1, unique per language (curriculum ends at 5000; higher ranks form the voluntary extension) |
| lemma | yes | dictionary form |
| pos | no | Universal Dependencies UPOS (`NOUN`, `VERB`, ...). `(language, lemma, pos)` is the upsert key |
| translation_cs | yes | primary Czech gloss(es) |
| ipa | no | without slashes |
| cefr | no | `A1`..`C2` |
| gender | no | `der/die/das`, `m/f` |
| example | no | short example sentence in the target language |
| source, license, revision | no | provenance of the row (e.g. `polyflow-curated`, `CC0-1.0`, `core100-v1`) |
| content_flags | no | pipe-separated (`violence\|profanity`): `sexual`, `profanity`, `violence`. Flagged items never reach child profiles. Re-imports only add flags (an admin's flag is never dropped); remove a flag via `PATCH /api/v1/lexicon/{id}` |

The committed `*.core100.csv` files hold the **first 100 hand-curated lemmas per language** (plan P2): frequent
function words plus frequent concrete vocabulary suited to children. Ranks are an approximate frequency
order, not copied from a published corpus list; Czech glosses still need native-speaker review. Every row
carries `source`, `license` and `revision` columns (provenance); IPA is left blank where unverified.
Examples should contain the lemma's citation form where natural: recall tasks only show a cloze when the
lemma occurs verbatim in the example.

### Producing the full lists (not done yet)

Target per language: 5,000 lemmas for the curriculum (full B2), plus an optional extension (6,000+)
used only for voluntary, recognition-focused practice.

No single open dataset provides "top-N *lemmas* + Czech glosses + IPA + CEFR" for DE/FR/IT/EN. A realistic pipeline:

1. **Frequency**: lemmatise a large corpus with spaCy/Stanza and count, or use an existing lemma list.
   Surface-form lists (e.g. OpenSubtitles-derived `FrequencyWords`, CC-BY-SA-4.0) are *not* lemma lists:
   `bin/bist/ist/sind` would occupy four ranks. Licences differ per source; check before redistributing.
2. **Czech glosses + IPA**: Wiktionary extracts (kaikki.org, CC-BY-SA) cover most of the top few thousand;
   coverage of glosses/IPA thins out toward rank 5,000+. Gaps filled by LLM/MT and **reviewed by a human**. Unreviewed glosses will teach wrong meanings.
3. **CEFR**: no authoritative open per-lemma CEFR mapping exists for these languages; derive a
   heuristic from rank bands or leave blank.

Import is an idempotent upsert: re-running updates rank/gloss/etc. in place without touching user progress.
The per-language rank constraint is deferred to commit, so rank shifts inside one file are fine; an import
fails cleanly if an item *not* in the file still holds a rank the file assigns to another lemma.

## Scenes (`scenes/*.json`)

Short dialogues that open each lesson (Lekce): the learner reads the scene first (Czech translation on
demand, new words highlighted and tappable), then meets each new word, then practises it. Practice is
never graded; only the separate check (Ověření) counts toward knowing a word.

Format and rules are in `app/domain/scenes.py`. In a line, `[Hund]` marks a lexicon word whose surface
form is the lemma, `[bin|sein]` an inflected form, `[sie|sie/PRON]` a lemma that needs its UPOS. `words`
lists the lemmas a scene introduces: every word at most once per language, and marked at least once in
that scene. Lessons walk scenes in file order, up to 4 new words per lesson; words with no scene follow
by frequency with their example sentence as context.

Import after the lexicon: `python -m app.cli seed-scenes data/scenes/*.json` (`--dry-run` validates
against the lexicon in the database). `tests/test_scene_data.py` checks the committed files against the
committed lexicon and requires every core-100 word to have a scene. The `*.core100.json` files
(revision `scenes-v1`) were drafted without native-speaker review; target-language grammar and the
Czech translations still need it.

## Content blacklist (`blacklist/*.csv`)

Columns: `language,pattern_type,pattern,category,note`. Blank `language` = all languages.
`keyword` = whole-word, case-insensitive; `regex` = Python `re`, compiled case-insensitively and
validated at import time.
