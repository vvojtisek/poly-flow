# Seed data

## Lexicon (`lexicon/*.csv`)

Columns: `language,rank,lemma,pos,translation_cs,ipa,cefr,gender,example`. Lines starting with `#` are comments.

| column | required | notes |
|---|---|---|
| language | yes | `de` / `fr` / `it` |
| rank | yes | 1..2500, unique per language |
| lemma | yes | dictionary form |
| pos | no | Universal Dependencies UPOS (`NOUN`, `VERB`, ...). `(language, lemma, pos)` is the upsert key |
| translation_cs | yes | primary Czech gloss(es) |
| ipa | no | without slashes |
| cefr | no | `A1`..`C2` |
| gender | no | `der/die/das`, `m/f` |
| example | no | short example sentence in the target language |

The committed `*.sample.csv` files hold **20 hand-curated lemmas per language** for pipeline testing only.
Ranks there are approximate.

### Producing the full 2,500-lemma lists (not done yet)

No single open dataset provides "top-N *lemmas* + Czech glosses + IPA + CEFR" for DE/FR/IT. A realistic pipeline:

1. **Frequency**: lemmatise a large corpus with spaCy/Stanza and count, or use an existing lemma list.
   Surface-form lists (e.g. OpenSubtitles-derived `FrequencyWords`, CC-BY-SA-4.0) are *not* lemma lists:
   `bin/bist/ist/sind` would occupy four ranks. Licences differ per source; check before redistributing.
2. **Czech glosses + IPA**: Wiktionary extracts (kaikki.org, CC-BY-SA) cover most of the top 2,500;
   gaps filled by LLM/MT and **reviewed by a human**. Unreviewed glosses will teach wrong meanings.
3. **CEFR**: no authoritative open per-lemma CEFR mapping exists for these languages; derive a
   heuristic from rank bands or leave blank.

Import is an idempotent upsert: re-running updates rank/gloss/etc. in place without touching user progress.
The per-language rank constraint is deferred to commit, so rank shifts inside one file are fine; an import
fails cleanly if an item *not* in the file still holds a rank the file assigns to another lemma.

## Content blacklist (`blacklist/*.csv`)

Columns: `language,pattern_type,pattern,category,note`. Blank `language` = all languages.
`keyword` = whole-word, case-insensitive; `regex` = Python `re`, compiled case-insensitively and
validated at import time.
