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

### `en.0101-1000.csv` (English ranks 101-1000, revision `en1000-draft-v2`)

900 words that take the English course from the core-100 to the A2 milestone (1,000), so the
placement test can place up to 1,000 and the A1 and A2 level exams can open. Lemmas, in order,
come from `frequency/en_GB.lemmas.csv`: walk the list from rank 1, skip the core-100 lemmas and
the inflected forms `higher` and `lower`, and number the rest 101-1000. Lessons therefore follow
frequency after the core block. A list entry that merges several words takes its most frequent
use (`bear` -> `born`, `unite` -> `united`, `china` -> `China`); the other senses (`bear` =
carry and the animal, the verb `unite`, `china` = porcelain) join a later block as words of their
own. These words have no scene: a lesson shows each word's example sentence as its context.

Profanity (`shit`, `fuck`, `fucking`, `damn`, `hell`, `ass`) sits at its frequency rank with the
`profanity` flag. Adults get it only after opting in (Nastavení, `settings.learn_profanity`);
child profiles never get any flagged item.

Czech glosses, part of speech and the British English examples were drafted by Claude and have
**not been reviewed by a native Czech speaker** (`source` = `claude-drafted`); the review list,
with every gloss, is kept with the project files (`reviews/en-101-1000-review.md`). Glosses are
unique across the English lexicon, because recall shows the gloss and expects one word;
near-synonyms carry a bracket (`large` = `velký (rozměrný)`). Where the list's POS tag is an
artefact of tagging isolated words, the lexicon uses the common learner sense (`step` NOUN, `key`
NOUN, `count` VERB). Lemmas that differ from the list: `according to` (`according`), `per cent`
(`percent`), `born` (`bear`), `united` (`unite`), `China` (`china`). Content flags carry over from
the frequency list, plus `battle` (violence) and `fucking` (profanity, missing from
`en.flags.csv`); IPA and CEFR are blank. Licence CC-BY-SA-4.0, because the selection and order
derive from wordfreq. `tests/test_lexicon_data.py` checks ranks 1-1000 without gaps, unique
glosses, the en_GB order, carried-over flags, and that no unflagged example uses a flagged word.

### `en.1001-5000.csv` (English ranks 1001-5000, revision `en5000-draft-v1`)

4,000 words that take the English course from the A2 milestone (1,000) through B1 (2,500) and the
B2 threshold (4,000) to full B2 (5,000), so the placement test can place up to 5,000 and the B1
and B2 level exams can open. Same method as ranks 101-1000: walk `frequency/en_GB.lemmas.csv`
from where the previous block stopped (en_GB rank 1002), skip lemmas already in the lexicon, and
number the rest 1001-5000. 68 list entries were skipped because they are not useful headwords for
a Czech learner: proper names and name fragments (`victor`, `bailey`, `sander`), prefixes and
clippings (`anti`, `sub`, `micro`, `mod`), fillers (`uh`, `um`, `hmm`), archaic forms (`thou`,
`thee`), drug names (`marijuana`, `cannabis`, `cocaine`, `coke`, `dope`) and US-only or slang
entries (`interstate`, `capitol`, `cum`); the file header lists the policy. Where the list's POS
tag is an artefact (`ant` ADJ, `brutal` NOUN, `vein` ADV), the row uses the learner sense.
Language and nationality nouns are capitalised (`Czech`, `Arabic`, `Portuguese`).

Flags: profanity and sexual vocabulary carry `profanity` or `sexual` (adult opt-in only, never in
child profiles); violent vocabulary carries `violence` (`weapon`, `bomb`, `hostage`, `massacre`,
`pistol`, `warfare`...), added by hand where the frequency list has no flag. Examples of unflagged
words use no flagged word. 97.5% of examples contain the lemma verbatim (cloze).

**Not reviewed by a native Czech speaker** (`source` = `claude-drafted`, licence CC-BY-SA-4.0 as
the order derives from wordfreq). The review list is kept with the project files
(`reviews/en-1001-5000-review.md`). Still open: the second senses of `bear` (animal, carry),
`unite` (verb) and `china` (porcelain), which need their own rows outside the frequency order.
`tests/test_lexicon_data.py` checks ranks 1-5000 without gaps, unique glosses, en_GB order,
provenance, carried-over flags and clean examples, and that the A1-B2 exam bands are complete.

### `de.0101-1000.csv` (German ranks 101-1000, revision `de1000-draft-v1`)

900 words that take the German course from the core-100 to the A2 milestone (1,000), so the
placement test and the A1 and A2 level exams can open for German. Unlike English there is no
German lemma frequency list in the repository yet: lemmas and their order were **drafted by
Claude from general knowledge** of frequent, learner-relevant German (function words, everyday
nouns with gender, common verbs and adjectives, numbers, days and months), not copied from a
published corpus list. Words that are not suitable for child profiles (alcohol, smoking) were
left out of this block rather than flagged. Each row has a Czech gloss, gender for nouns
(`der/die/das`; `die` for plural-only nouns such as `Eltern`, none for country and language names
used without an article) and one example sentence; for verbs the example uses the infinitive,
so recall can show a cloze. Reflexive verbs are listed without `sich` and say so in the gloss
(`freuen` = `radovat se (sich freuen)`). Glosses are unique across the German lexicon.
**Not reviewed by a native speaker** (`source` = `claude-drafted`, licence CC0-1.0). These words
have no scene: a lesson shows each word's example sentence as its context.
`tests/test_lexicon_de.py` checks ranks 1-1000 without gaps, unique keys and glosses,
provenance, noun capitalisation and gender. Adding `sein/DET` (possessive) made `sein` and `zu`
ambiguous in scene markup, so `de.core100.json` now writes `sein/AUX` and `zu/ADP`.

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

## Frequency lemmas (`frequency/*.lemmas.csv`)

Ranked reference lists of the most frequent lemmas per locale, imported into the `frequency_lemmas`
table. Columns: `rank,lemma,pos,content_flags,source,license,revision`; the locale comes from the
file name (`en_GB.lemmas.csv`). Ranks run exactly 1..N, lemmas are unique per locale, lowercase ASCII
(`app/domain/lemmas.py`). `content_flags` has the same meaning as in the lexicon.

**This is not curriculum.** Rows have no Czech gloss, so lessons, Ověření, level exams and the
placement test never draw from this table; they keep using `lexicon_items`. The list is the rank
source for growing the lexicon: a word joins the lexicon (and the courses) once it has a reviewed
Czech gloss, with its rank taken from here. Ranks map onto the ladder with
`app.domain.progression.frequency_band` (stored as `frequency_band`): 1-100 core, -500 A1, -1000 A2,
-2500 B1, -4000 B2 threshold, -5000 full B2, 5001-10000 the voluntary passive extension.

Import (idempotent; one transaction, batches of 1,000; lemmas missing from the file are deleted,
flags are only ever added):

```sh
python -m app.cli seed-lemmas data/frequency/*.lemmas.csv [--dry-run]
```

### `en_GB.lemmas.csv` and `en_US.lemmas.csv` (10,000 lemmas each, revision `wordfreq-en-v1`)

The English course teaches British English (decided 2026-10-04), so `en_GB` is the list it will draw
ranks from; `en_US` stays as an American reference. Both come from the same pipeline and the same
reviewed lists (`en.*.csv`), and differ only in spelling and in the dictionary that filters them.
Generated, not hand-edited: `uv run --extra lemmas python scripts/seed_lemmas_en.py build --locale
en_GB` (or `en_US`); pinned versions in `pyproject.toml`; the output is byte-identical on re-runs.

1. Word forms and frequencies: [wordfreq](https://github.com/rspeer/wordfreq) 3.1.1, `en`, top 60,000.
2. Normalise: NFKD, drop diacritics, lowercase; British spellings mapped to American with breame
   0.1.2 (only when Hunspell knows the American form), so both spellings of a word count together.
3. Lemmatise each form with spaCy 3.8 `en_core_web_sm` 3.8.0 and add its frequency to the lemma;
   contractions split (`don't` -> do + not). Forms tagged PROPN out of context are re-lemmatised as
   nouns; forms left unlemmatised are retried as each open class. `en.lemma_overrides.csv` corrects
   known errors (`data` stays `data`, `better` -> `good`).
4. en_GB only: map each lemma to British spelling with breame (`color` -> `colour`, `realize` ->
   `realise`). `en_GB.spelling.csv` corrects the map: it keeps American forms that are also British
   words with their own meaning (`tire`, `program`, `practice`, `draft`) and adds `math` -> `maths`,
   `mom` -> `mum`.
5. Keep a lemma only if the locale's pinned Hunspell dictionary (LibreOffice/dictionaries, pinned commit
   and checksums; SCOWL `en_US`, LibreOffice `en_GB` with -ise spellings) accepts it in lowercase. This
   drops names, places, acronyms, the other variety's spellings, most foreign words and slang. The
   `en_GB` dictionary accepts many names in lowercase, so a British lemma must also pass `en_US` in its
   American spelling (or be listed in `en_GB.spelling.csv`). `en.include.csv` re-admits capitalised
   everyday words (days, months, languages and nationalities, holidays) and `seize`, which the `en_GB`
   dictionary lacks; `en.exclude.csv` removes what the dictionaries let through (abbreviations, roman
   numerals, first names, prefix fragments).
6. Rank by summed frequency (ties alphabetical), keep 10,000. `en.flags.csv` adds content flags.

The two lists share 9,784 lemmas. The 216 that differ are spelling variants (`colour`/`color`) and
words only one variety uses (`mum`, `maths`, `jewellery` against `mom`, `downtown`, `sidewalk`).

Limits, stated plainly:

- **Not COCA.** COCA's lemma lists are licensed and not freely downloadable, so wordfreq is the source.
  wordfreq's English blends US and UK sources (Wikipedia, subtitles, news, books, web, Reddit,
  Twitter). The locale means spelling and vocabulary filter, not a national corpus; ranks are the
  same blended frequencies in both lists. wordfreq's data stops around 2021 and the project is no
  longer updated, so recent words rank low or are missing.
- Lemmas and POS come from tagging isolated words, without sentence context. POS is the dominant tag
  of the lemma's forms and is a heuristic; homographs are merged (`left` counts toward `leave`).
  Where an American spelling covers two British words (`tire`/`tyre`, `meter`/`metre`), the whole
  frequency goes to one of them.
- The 100 English core lemmas are in both lists (99 within the first 1,000, `cat` at ~1,100). The
  lexicon's core-100 ranks are hand-set and unchanged; nothing here changes learner progress.
- Content flags are a first, hand-made pass (profanity, slurs, sexual terms, war and killing as
  violence, as in the German blacklist). Identity terms are not flagged. Drugs have no `ContentFlag`
  value and are unflagged.
- Licence: wordfreq's data is CC-BY-SA-4.0, so these derived lists are too: attribution to wordfreq
  (Robyn Speer, <https://doi.org/10.5281/zenodo.7199437>) sits in the file header, every row carries
  `source` and `license`, and the table keeps both. wordfreq's README asks people not to convert it to
  CSV because attribution gets stripped; the files hold ranks of processed lemmas, not wordfreq's
  frequencies, and keep the attribution in every row. spaCy, breame (Apache-2.0), spylls (MPL-2.0) and
  the Hunspell dictionaries (SCOWL; en_GB under LGPL) are build tools only; none of their data is
  copied into the lists beyond the lemmas themselves.

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

## CEFR diagnostic item banks (`diagnostic/<lang>.diagnostic.json`, revision `diag-v1`)

Item banks for part 2 of the placement test (*Rozřazovací test: gramatika a porozumění*,
`app.domain.diagnostic`, policy `d1`). Each language holds 40 items, 8 per band A1, A2, B1, B2
and C1. The C1 band is the **above-B2 probe**: the app reports it as "B2+", never as a C1
result. Skills: `grammar` (verb forms, cases, subordinate-clause word order, conditionals,
subjunctive, passive, inversion), `vocabulary` (words in context), `reading` (a short passage,
question in Czech), `listening` (`audio` is spoken by TTS and shown only after answering; the
test leaves listening out when the language's voice is not installed) and `idiom`.

Fields: `id`, `level`, `skill`, `prompt`, `context` (reading only), `audio` (listening only),
`options` (3-5, unique), `answer` (one of the options), `explain` (Czech), `content_flags`.
Files are loaded at runtime (no seed step); a session stores the asked item ids, so editing a
bank never changes a finished test. `tests/test_diagnostic_domain.py` validates every bank.

Drafted by Claude on 2026-11-06, **not reviewed** by a teacher or a native speaker
(`review_status: unreviewed`). Difficulties are the nominal band of each item, not calibrated
on learner data; recalibrate with a new policy version once real answers exist.

### Adaptive policy (d1)

The diagnostic starts at A2 (theta -1) unless the separate vocabulary estimate provides a
starting prior. Each answer updates a posterior over A1, A2, B1, B2, and the above-B2 probe
(reported only as B2+). The next unused item is selected for information near the current
posterior mean, with ties rotated across skills; item order within a band is randomized by the
session RNG. The saved asked-item IDs prevent repeats. It requires at least 10 answers and stops
once posterior standard deviation is at most 0.42, the bank is exhausted, or 22 questions have
been asked. An incomplete attempt does not replace the last completed result. The estimate is
uncertain and pilot-calibrated; at B2+ it only means performance exceeded this bank's B2 items,
not that C1/C2 was assessed or certified.

## Grammar packs (`grammar/<lang>.grammar.json`)

Grammar packs contain editable Czech explanations, examples, and exercises. Every course
language has a draft A1-A2 syllabus (added 2026-11-06, revision in brackets):

| pack | A1 | A2 | above A2 |
|---|---|---|---|
| `de.grammar.json` (`grammar-v2`) | 15 units | 11 units | B1 6, B2 5 |
| `fr.grammar.json` (`grammar-fr-v1`) | 13 units | 10 units | none yet |
| `it.grammar.json` (`grammar-it-v1`) | 12 units | 9 units | none yet |
| `en.grammar.json` (`english-grammar-v2`) | 13 units | 10 units | one introductory unit each B1-C2 |

The A1-A2 topics follow the usual CEFR grammar inventories for each language (verb *be*/*have*,
present tense and irregular verbs, articles and gender, plurals and agreement, negation and
questions, possessives, prepositions, imperative at A1; past tenses, object pronouns, future,
comparison, modal verbs, reflexive verbs and the language's typical A2 points at A2). They were
drafted by Claude (`source`, `review_status: unreviewed`) and still need a teacher or native
speaker's review; `tests/test_grammar_domain.py` requires at least 8 units at A1 and at A2 for
every language and checks that every shown answer grades as correct. Packs are marked unreviewed
until a teacher or qualified reviewer approves them. Adding a unit is additive and keyed by
stable unit ID, so importing a new pack preserves learner progress. Each unit has a short
`summary` for discovery and an `objective` describing an observable outcome; older packs may omit
`objective`, in which case the importer reuses the summary.
