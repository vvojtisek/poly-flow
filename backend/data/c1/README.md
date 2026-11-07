# C1 vocabulary review drafts (5001–8000)

Product definition requested on 2026-11-07: B2 ends at 5,000 words; **C1 vocabulary**
continues through 8,000. This is an application vocabulary band, not a validated
CEFR assessment. The existing required curriculum and A1–B2 exams remain intact.

Each language (DE, British EN, FR, IT) has 3,000 **unreviewed candidates** in the
existing `LexiconRow` CSV schema. Existing ranks 1–5000, keys, and learner progress
are untouched. These files deliberately live outside `data/lexicon/*.csv` and are
**not included in the default seed command**. Review meanings, senses, spelling,
regional usage, child suitability and ordering before importing them. Do not use
these candidates as a verified level list for strict 95/5 story validation.

## Sources and limitations

Czech glosses, POS and noun gender are extracted from the WikDict 2025.11.21
DE/EN/FR/IT→CS TEI dictionaries: Karl Bartel/WikDict, Wiktionary contributors,
via DBnary. Exact download URLs and SHA-256 hashes are in `sources.json`.
The TEI files declare **CC-BY-SA-3.0**; this modified selection is distributed
under **CC-BY-SA-4.0**, an allowed later ShareAlike version. Attribution and links:
https://www.wikdict.com/page/about, https://www.wiktionary.org/,
http://kaiko.getalp.org/about-dbnary/, https://creativecommons.org/licenses/by-sa/3.0/,
https://creativecommons.org/licenses/by-sa/4.0/.

Ordering uses wordfreq 3.1.1 (Robyn Speer, https://doi.org/10.5281/zenodo.7199437;
frequency data CC-BY-SA-4.0), descending Zipf score, then lemma. simplemma 1.1.2
(MIT, build tool only) removes recognised inflected forms. The script excludes
existing lemmas, proper-name markers, selected sensitive entries and confirmed
bad dictionary pairs. Nouns need source gender outside English. No synthetic
examples or IPA are supplied; optional fields stay blank.

**Not today's exact top 8,000 lemmas.** wordfreq's corpora stop around 2021,
WikDict has coverage gaps and incorrect automated sense links, and the existing
5,000-word curriculum is preserved. These are the most frequent remaining
eligible dictionary candidates, not continuous ranks from an authoritative corpus.
Dictionary coverage is particularly thin for Italian: the tail includes uncommon
terms. Rank is a proposed teaching order. British spelling and individual meanings
still require review. Sample exclusions include Italian `mettersi` → `sada` and
`salvatore` → `úspory`. Filtering cannot establish semantic correctness or safety.

## Reproduction and review

Outside the runtime environment, install the build-only tools in a separate venv:

```sh
uv venv /workspace/c1-tools
uv pip install --python /workspace/c1-tools/bin/python wordfreq==3.1.1 simplemma==1.1.2
# Download each sources.json URL into a folder as wd-deu.tei, wd-eng.tei,
# wd-fra.tei and wd-ita.tei, keeping TLS verification enabled.
/workspace/c1-tools/bin/python scripts/draft-c1-vocabulary.py --sources /path/to/downloads
```

The script verifies source checksums before writing; source changes require an
explicit review and manifest update. It never imports data or changes existing ranks.

After reviewing a file, validate using the established command from `backend/`:

```sh
uv run python -m app.cli seed-lexicon data/c1/en.5001-8000.csv --dry-run
# Only after content review:
uv run python -m app.cli seed-lexicon data/c1/en.5001-8000.csv
```

An import into a deployment that already uses extension ranks needs a collision
review first. No command in this PR resets or shifts existing extension entries.
