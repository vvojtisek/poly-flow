"""Build and seed the 10,000 most frequent en_US lemmas (frequency reference list).

    uv run --extra lemmas python scripts/seed_lemmas_en_us.py build   # source -> CSV
    uv run python scripts/seed_lemmas_en_us.py seed [--dry-run]       # CSV -> database
    uv run --extra lemmas python scripts/seed_lemmas_en_us.py all     # both

`build` needs the optional `lemmas` extra (wordfreq, spaCy + en_core_web_sm, breame) and
rewrites the committed `data/frequency/en_US.lemmas.csv`. `seed` needs only the app: it is
`python -m app.cli seed-lemmas` on that file, so the database import never depends on the
network or on the NLP library versions. Run from `backend/`.

Pipeline (see data/README.md, "Frequency lemmas"):
1. Word forms: wordfreq `top_n_list("en", CANDIDATES)` with their frequencies.
2. Normalise: Unicode NFKD, drop diacritics, lowercase, strip; British spellings mapped to
   American with breame (en_US).
3. Lemmatise each form with spaCy en_core_web_sm (contractions split: "don't" -> do + not)
   and add the form's frequency to each lemma. Corrections in `en_US.lemma_overrides.csv`.
4. Drop: anything but [a-z] words (hyphenated compounds allowed), single letters other than
   "a" and "i", lemmas the pinned SCOWL en_US dictionary does not list in lowercase (proper
   nouns, acronyms, British-only spellings, foreign words, most slang), and the reviewed list
   in `en_US.exclude.csv`. `en_US.include.csv` keeps capitalised everyday words the
   dictionary only lists capitalised (days, months, nationalities and languages, holidays).
5. Rank lemmas by summed frequency (ties: alphabetical), keep exactly LIMIT.
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
OUT = DATA / "en_US.lemmas.csv"
EXCLUDE = DATA / "en_US.exclude.csv"
INCLUDE = DATA / "en_US.include.csv"
OVERRIDES = DATA / "en_US.lemma_overrides.csv"
FLAGS = DATA / "en_US.flags.csv"

LOCALE = "en_US"
LIMIT = 10_000
CANDIDATES = 60_000  # word forms read from wordfreq; enough to fill LIMIT after filtering
# SCOWL en_US Hunspell dictionary (LibreOffice/dictionaries), used only as a filter via
# spylls: a lemma is kept when Hunspell accepts it in lowercase. Proper nouns ("London") and
# acronyms ("TV") are only accepted capitalised, British-only spellings ("colour") not at all.
DICTIONARY_BASE = (
    "https://raw.githubusercontent.com/LibreOffice/dictionaries/"
    "32b006a2c22a4ac7e8ed3f03346f7b3d85a970a4/en/en_US"
)
DICTIONARY_SHA256 = {
    ".dic": "f0b1a234bd178bdd01875b2a392a9647f888b8fe879f79c52aae62c2759b3647",
    ".aff": "e746c882dd6f303c2c46e7452804b9201115a6942cfeb15f18f8edf774d2e24e",
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


def us_dictionary():
    """The pinned en_US Hunspell dictionary (downloaded once, checksums verified)."""
    from spylls.hunspell import Dictionary

    folder = CACHE / f"hunspell-{DICTIONARY_SHA256['.dic'][:12]}"
    for ext, digest in DICTIONARY_SHA256.items():
        path = folder / f"en_US{ext}"
        if path.exists():
            continue
        folder.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(DICTIONARY_BASE + ext, timeout=60) as resp:
            body = resp.read()
        if hashlib.sha256(body).hexdigest() != digest:
            raise SystemExit(f"checksum mismatch for {DICTIONARY_BASE + ext}")
        path.write_bytes(body)
    return Dictionary.from_files(str(folder / "en_US"))


def build(out: Path = OUT, report: Path | None = None) -> int:
    import spacy
    from breame.data.spelling_constants import BRITISH_ENGLISH_SPELLINGS
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
    hunspell = us_dictionary()

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

    forms: dict[str, float] = defaultdict(float)
    for word in top_n_list("en", CANDIDATES):
        norm = strip_diacritics(word).lower().strip()
        if norm != word.lower() and len(norm) == 1:
            continue  # "à" is not the article "a"
        forms[us_spelling(norm)] += word_frequency(word, "en")

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
            freq_by_lemma[lemma] += forms[text]
            pos_mass[lemma][tok.pos_] += forms[text]

    rows = []
    dropped: dict[str, int] = defaultdict(int)
    dropped_rows: list[tuple[str, str, str, float]] = []
    for lemma, freq in sorted(freq_by_lemma.items(), key=lambda kv: (-kv[1], kv[0])):
        pos = max(pos_mass[lemma].items(), key=lambda kv: (kv[1], kv[0]))[0]
        if not is_valid_lemma(lemma):
            reason = "format"
        elif lemma in excluded:
            reason = "excluded"
        elif not is_us_word(lemma):
            reason = "not_lowercase_us_word"  # names, acronyms, British-only, foreign, slang
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

    versions = {p: version(p) for p in ("wordfreq", "spacy", "en_core_web_sm", "breame", "spylls")}
    source = f"wordfreq-{versions['wordfreq']}"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as fh:
        fh.write(
            f"# {LIMIT} most frequent {LOCALE} lemmas. Generated by scripts/seed_lemmas_en_us.py"
            "; do not edit by hand.\n"
            "# Derived from wordfreq (Robyn Speer, https://doi.org/10.5281/zenodo.7199437),"
            " whose data is CC-BY-SA-4.0; this list is shared under the same licence.\n"
            f"# Source: wordfreq {versions['wordfreq']} 'en' (data CC-BY-SA-4.0, blended"
            " sources, not US-only); lemmas and POS: spaCy"
            f" {versions['spacy']} en_core_web_sm {versions['en_core_web_sm']} on isolated"
            f" forms (heuristic); US spelling: breame {versions['breame']}; word filter:"
            " SCOWL en_US Hunspell (LibreOffice/dictionaries 32b006a) via spylls"
            f" {versions['spylls']}.\n"
            f"# Dropped before rank {LIMIT}: "
            + ", ".join(f"{k} {v}" for k, v in sorted(dropped.items()))
            + "\n"
        )
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["rank", "lemma", "pos", "content_flags", "source", "license", "revision"])
        for rank, (lemma, pos) in enumerate(rows, start=1):
            w.writerow([rank, lemma, pos, flags.get(lemma, ""), source, "CC-BY-SA-4.0", REVISION])
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
    parser.add_argument("--path", type=Path, default=OUT)
    parser.add_argument("--report", type=Path, help="build: write the dropped lemmas here")
    parser.add_argument("--dry-run", action="store_true", help="seed: validate only")
    args = parser.parse_args(argv)
    if args.step in ("build", "all") and (rc := build(args.path, args.report)):
        return rc
    if args.step in ("seed", "all"):
        return seed(args.path, args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
