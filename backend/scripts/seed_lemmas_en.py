"""Build and seed the 10,000 most frequent English lemmas per locale (en_GB, en_US).

    uv run --extra lemmas python scripts/seed_lemmas_en.py build --locale en_GB  # source -> CSV
    uv run python scripts/seed_lemmas_en.py seed --locale en_GB [--dry-run]      # CSV -> database
    uv run --extra lemmas python scripts/seed_lemmas_en.py all --locale en_GB    # both

`build` needs the optional `lemmas` extra (wordfreq, spaCy + en_core_web_sm, breame, spylls)
and rewrites the committed `data/frequency/<locale>.lemmas.csv`. `seed` needs only the app:
it is `python -m app.cli seed-lemmas` on that file, so the database import never depends on
the network or on the NLP library versions. Run from `backend/`.

Pipeline (see data/README.md, "Frequency lemmas"):
1. Word forms: wordfreq `top_n_list("en", CANDIDATES)` with their frequencies.
2. Normalise: Unicode NFKD, drop diacritics, lowercase, strip; British spellings mapped to
   American with breame, so both spellings of a word count together.
3. Lemmatise each form with spaCy en_core_web_sm (contractions split: "don't" -> do + not)
   and add the form's frequency to each lemma. Corrections in `en.lemma_overrides.csv`.
4. en_GB only: map each lemma to British spelling with breame ("color" -> "colour"), with
   corrections in `en_GB.spelling.csv` (keeps "tire" and "program", which are also British
   words with their own meaning; adds "math" -> "maths", "mom" -> "mum").
5. Drop: anything but [a-z] words (hyphenated compounds allowed), single letters other than
   "a" and "i", lemmas the locale's pinned Hunspell dictionary does not accept in lowercase
   (proper nouns, acronyms, the other variety's spellings, foreign words, most slang; en_GB
   lemmas must also pass en_US in their American spelling, which screens out names), and
   the reviewed list in `en.exclude.csv`. `en.include.csv` keeps capitalised everyday words
   the dictionaries only list capitalised (days, months, nationalities and languages,
   holidays).
6. Rank lemmas by summed frequency (ties: alphabetical), keep exactly LIMIT.
"""

import argparse
import csv
import functools
import hashlib
import sys
import unicodedata
import urllib.request
from collections import defaultdict
from importlib.metadata import version
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
DATA = BACKEND / "data" / "frequency"
EXCLUDE = DATA / "en.exclude.csv"
INCLUDE = DATA / "en.include.csv"
OVERRIDES = DATA / "en.lemma_overrides.csv"
FLAGS = DATA / "en.flags.csv"
SPELLING_GB = DATA / "en_GB.spelling.csv"

LOCALES = ("en_GB", "en_US")
LIMIT = 10_000
CANDIDATES = 60_000  # word forms read from wordfreq; enough to fill LIMIT after filtering
# Hunspell dictionaries from LibreOffice/dictionaries at a pinned commit, used only as filters
# via spylls: a lemma is kept when Hunspell accepts it in lowercase. Proper nouns ("London")
# and acronyms ("TV") are only accepted capitalised, the other variety's spellings not at all.
# en_US is SCOWL's; en_GB is the LibreOffice British list (-ise spellings).
DICTIONARY_BASE = (
    "https://raw.githubusercontent.com/LibreOffice/dictionaries/"
    "32b006a2c22a4ac7e8ed3f03346f7b3d85a970a4/en/"
)
DICTIONARY_SHA256 = {
    "en_US": {
        ".dic": "f0b1a234bd178bdd01875b2a392a9647f888b8fe879f79c52aae62c2759b3647",
        ".aff": "e746c882dd6f303c2c46e7452804b9201115a6942cfeb15f18f8edf774d2e24e",
    },
    "en_GB": {
        ".dic": "04e90f34f5263bf26780e9c4a442e9ad16584e227af49ddd1b3b21b01df5b29c",
        ".aff": "0fd6ed120ef28957847d98ba5149b117e27116cf81b5aa36208453f6755a36fd",
    },
}
DICTIONARY_NAME = {
    "en_US": "SCOWL en_US Hunspell",
    "en_GB": "LibreOffice en_GB Hunspell",
}
CACHE = Path.home() / ".cache" / "polyflow"
REVISION = "wordfreq-en-v1"
CLOSED_CLASS = {"ADP", "AUX", "CCONJ", "DET", "NUM", "PART", "PRON", "SCONJ"}

sys.path.insert(0, str(BACKEND))


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(line for line in fh if not line.lstrip().startswith("#")))


def strip_diacritics(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def hunspell_dictionary(locale: str):
    """The locale's pinned Hunspell dictionary (downloaded once, checksums verified)."""
    from spylls.hunspell import Dictionary

    digests = DICTIONARY_SHA256[locale]
    folder = CACHE / f"hunspell-{digests['.dic'][:12]}"
    for ext, digest in digests.items():
        path = folder / f"{locale}{ext}"
        if path.exists():
            continue
        folder.mkdir(parents=True, exist_ok=True)
        url = f"{DICTIONARY_BASE}{locale}{ext}"
        with urllib.request.urlopen(url, timeout=60) as resp:
            body = resp.read()
        if hashlib.sha256(body).hexdigest() != digest:
            raise SystemExit(f"checksum mismatch for {url}")
        path.write_bytes(body)
    return Dictionary.from_files(str(folder / locale))


def lemma_file(locale: str) -> Path:
    return DATA / f"{locale}.lemmas.csv"


def build(locale: str, out: Path, report: Path | None = None) -> int:
    import spacy
    from breame.data.spelling_constants import (
        AMERICAN_ENGLISH_SPELLINGS,
        BRITISH_ENGLISH_SPELLINGS,
    )
    from wordfreq import top_n_list, word_frequency

    from app.domain.lemmas import SINGLE_LETTER_WORDS, is_valid_lemma

    excluded = {r["lemma"] for r in _read_csv(EXCLUDE)}
    included = {r["lemma"] for r in _read_csv(INCLUDE)}
    overrides = {r["form"]: r["lemma"] for r in _read_csv(OVERRIDES)}
    flags = {r["lemma"]: r["content_flags"] for r in _read_csv(FLAGS)}

    nlp = spacy.load("en_core_web_sm", disable=["parser", "ner"])
    lemmatizer = nlp.get_pipe("lemmatizer")
    # Base forms of WordNet (spaCy's English lemma index); used to spot unlemmatised forms.
    base_forms = set().union(*lemmatizer.lookups.get_table("lemma_index").values())
    hunspell = hunspell_dictionary("en_US")
    target = hunspell if locale == "en_US" else hunspell_dictionary(locale)
    spelling_gb = {r["american"]: r["british"] for r in _read_csv(SPELLING_GB)}
    reviewed_gb = set(spelling_gb.values())

    def open_class_lemma(word: str, pos: str) -> tuple[str, str]:
        for candidate_pos in ("VERB", "NOUN", "ADJ", "ADV"):
            tok = nlp.make_doc(word)[0]
            tok.pos_ = candidate_pos
            lemma = lemmatizer.rule_lemmatize(tok)[0].lower()
            if lemma != word and lemma in base_forms:
                return lemma, candidate_pos
        return word, pos

    @functools.cache
    def is_us_word(w: str) -> bool:
        return w in SINGLE_LETTER_WORDS or w in included or hunspell.lookup(w)

    def us_spelling(w: str) -> str:
        # breame sometimes offers a rare US variant ("esthetic"); keep the form Hunspell knows.
        us = BRITISH_ENGLISH_SPELLINGS.get(w, w)
        return us if is_us_word(us) or not is_us_word(w) else w

    @functools.cache
    def is_target_word(w: str) -> bool:
        if locale == "en_US":
            return is_us_word(w)
        # The en_GB dictionary accepts many names in lowercase ("york", "simon"); the en_US
        # one does not, so a British lemma also needs its American equivalent to pass there.
        return (
            w in SINGLE_LETTER_WORDS
            or w in included
            or (
                target.lookup(w)
                and (
                    is_us_word(w)
                    or is_us_word(BRITISH_ENGLISH_SPELLINGS.get(w, w))
                    or w in reviewed_gb  # en_GB.spelling.csv
                )
            )
        )

    def target_spelling(w: str) -> str:
        if locale == "en_US":
            return w
        gb = spelling_gb.get(w) or AMERICAN_ENGLISH_SPELLINGS.get(w, w)
        return gb if is_target_word(gb) else w

    forms: dict[str, float] = defaultdict(float)
    for word in top_n_list("en", CANDIDATES):
        norm = strip_diacritics(word).lower().strip()
        if norm != word.lower() and len(norm) == 1:
            continue  # "à" is not the article "a"
        forms[us_spelling(norm)] += word_frequency(word, "en")

    excluded_target: set[str] = set()
    freq_by_lemma: dict[str, float] = defaultdict(float)
    pos_mass: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    texts = list(forms)
    for text, doc in zip(texts, nlp.pipe(texts, batch_size=2000), strict=True):
        for tok in doc:
            form = tok.text.lower()
            if tok.pos_ == "PROPN":
                # Lowercase forms tagged PROPN out of context are mostly common nouns
                # ("house", "games"); spaCy does not lemmatise PROPN, so redo it as NOUN.
                tok.pos_ = "NOUN"
                tok.lemma_ = lemmatizer.rule_lemmatize(tok)[0]
            lemma = overrides.get(form) or tok.lemma_.lower().strip()
            # Out of context the rule lemmatiser can invent stems ("beloved" -> "belove"):
            # keep the form when only the form is a dictionary word.
            if not is_us_word(lemma) and is_us_word(form):
                lemma = form
            if lemma not in base_forms and tok.pos_ not in CLOSED_CLASS and form not in overrides:
                # Mis-tagged out of context, an inflected form can survive as its own lemma
                # ("darker", "periods", "drank"): retry as each open class.
                lemma, tok.pos_ = open_class_lemma(lemma, tok.pos_)
            lemma = us_spelling(lemma)
            if lemma in excluded:  # the lists are keyed by the American form
                excluded_target.add(target_spelling(lemma))
            lemma = target_spelling(lemma)
            freq_by_lemma[lemma] += forms[text]
            pos_mass[lemma][tok.pos_] += forms[text]

    rows = []
    dropped: dict[str, int] = defaultdict(int)
    dropped_rows: list[tuple[str, str, str, float]] = []
    for lemma, freq in sorted(freq_by_lemma.items(), key=lambda kv: (-kv[1], kv[0])):
        pos = max(pos_mass[lemma].items(), key=lambda kv: (kv[1], kv[0]))[0]
        if not is_valid_lemma(lemma):
            reason = "format"
        elif lemma in excluded or lemma in excluded_target:
            reason = "excluded"
        elif not is_target_word(lemma):
            reason = "not_lowercase_word"  # names, acronyms, other variety, foreign, slang
        else:
            reason = ""
        if reason:
            dropped[reason] += 1
            dropped_rows.append((lemma, pos, reason, freq))
            continue
        rows.append((lemma, "" if pos in {"X", "SYM", "PUNCT", "SPACE"} else pos))
        if len(rows) == LIMIT:
            break
    if len(rows) < LIMIT:
        print(f"only {len(rows)} lemmas; raise CANDIDATES", file=sys.stderr)
        return 1

    flags_target = {target_spelling(k): v for k, v in flags.items()}
    versions = {p: version(p) for p in ("wordfreq", "spacy", "en_core_web_sm", "breame", "spylls")}
    source = f"wordfreq-{versions['wordfreq']}"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as fh:
        fh.write(
            f"# {LIMIT} most frequent {locale} lemmas. Generated by scripts/seed_lemmas_en.py"
            "; do not edit by hand.\n"
            "# Derived from wordfreq (Robyn Speer, https://doi.org/10.5281/zenodo.7199437),"
            " whose data is CC-BY-SA-4.0; this list is shared under the same licence.\n"
            f"# Source: wordfreq {versions['wordfreq']} 'en' (data CC-BY-SA-4.0, blended"
            " sources, not US-only); lemmas and POS: spaCy"
            f" {versions['spacy']} en_core_web_sm {versions['en_core_web_sm']} on isolated"
            f" forms (heuristic); spelling variants: breame {versions['breame']}; word filter:"
            f" {DICTIONARY_NAME[locale]} (LibreOffice/dictionaries 32b006a) via spylls"
            f" {versions['spylls']}.\n"
            f"# Dropped before rank {LIMIT}: "
            + ", ".join(f"{k} {v}" for k, v in sorted(dropped.items()))
            + "\n"
        )
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["rank", "lemma", "pos", "content_flags", "source", "license", "revision"])
        for rank, (lemma, pos) in enumerate(rows, start=1):
            w.writerow(
                [rank, lemma, pos, flags_target.get(lemma, ""), source, "CC-BY-SA-4.0", REVISION]
            )
    if report:
        with report.open("w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh, lineterminator="\n")
            w.writerow(["lemma", "pos", "reason", "frequency"])
            w.writerows((lem, p, r, f"{f:.3g}") for lem, p, r, f in dropped_rows)
    print(f"wrote {len(rows)} lemmas to {out}; dropped {dict(dropped)}")
    return 0


def seed(path: Path, dry_run: bool) -> int:
    from app.cli import main as cli_main

    return cli_main(["seed-lemmas", str(path), *(["--dry-run"] if dry_run else [])])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("step", choices=["build", "seed", "all"])
    parser.add_argument("--locale", choices=LOCALES, required=True)
    parser.add_argument("--path", type=Path, help="default: data/frequency/<locale>.lemmas.csv")
    parser.add_argument("--report", type=Path, help="build: write the dropped lemmas here")
    parser.add_argument("--dry-run", action="store_true", help="seed: validate only")
    args = parser.parse_args(argv)
    path = args.path or lemma_file(args.locale)
    if args.step in ("build", "all") and (rc := build(args.locale, path, args.report)):
        return rc
    if args.step in ("seed", "all"):
        return seed(path, args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
