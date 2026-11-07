"""The committed French and Italian lexicons (core-100 + drafted ranks 101-5000)."""

import re
from pathlib import Path

import pytest

from app.cli import LexiconRow, read_rows
from app.domain.enums import CefrLevel
from app.domain.level_exam import BY_LEVEL, band_complete

DATA = Path(__file__).resolve().parents[1] / "data" / "lexicon"
LANGS = ["fr"]
PROFANITY = {
    "fr": ("merde", "putain", "con", "connard", "salope", "foutre", "chier", "guerre", "tuer"),
}


def _rows(lang: str) -> list[LexiconRow]:
    return [r for p in sorted(DATA.glob(f"{lang}.*.csv")) for r in read_rows(p, LexiconRow)]


@pytest.mark.parametrize("lang", LANGS)
def test_ranks_run_1_to_5000_and_keys_are_unique(lang):
    rows = _rows(lang)
    assert sorted(r.rank for r in rows) == list(range(1, 5001))
    keys = [(r.lemma, r.pos) for r in rows]
    assert len(set(keys)) == len(keys)


@pytest.mark.parametrize("lang", LANGS)
def test_a1_to_b2_bands_count_as_imported(lang):
    ranks = [r.rank for r in _rows(lang)]
    for level in (CefrLevel.A1, CefrLevel.A2, CefrLevel.B1, CefrLevel.B2):
        band = BY_LEVEL[level]
        assert band_complete(band, sum(band.low < r <= band.high for r in ranks))


@pytest.mark.parametrize("lang", LANGS)
def test_glosses_are_unique(lang):
    """Recall shows the Czech gloss and expects one lemma: two words may not share a gloss."""
    glosses = [r.translation_cs for r in _rows(lang)]
    assert sorted({g for g in glosses if glosses.count(g) > 1}) == []


@pytest.mark.parametrize("lang", LANGS)
def test_drafted_block_is_marked_and_complete(lang):
    drafted = [r for r in _rows(lang) if r.rank > 100]
    assert len(drafted) == 4900
    for r in drafted:
        assert (r.source, r.license, r.revision) == (
            "claude-drafted",
            "CC-BY-SA-4.0",
            f"{lang}5000-draft-v1",
        ), r.lemma
        assert r.translation_cs and r.example, r.lemma
        if r.pos == "NOUN":
            assert r.gender in ("m", "f"), r.lemma
        else:
            assert not r.gender, r.lemma


@pytest.mark.parametrize("lang", LANGS)
def test_examples_are_single_sentences(lang):
    for r in _rows(lang):
        if r.rank > 100:
            assert re.match(r"^[«\"'A-ZÀ-Ö]", r.example), r.lemma
            assert r.example.rstrip()[-1] in ".!?»", r.lemma
            assert not re.search(r"[.!?] +[A-ZÀ-Ö]", r.example), r.lemma


@pytest.mark.parametrize("lang", LANGS)
def test_adult_and_violent_words_are_flagged(lang):
    """Adult-only vocabulary must carry a flag so child profiles never see it."""
    rows = {r.lemma: {f.value for f in r.content_flags} for r in _rows(lang)}
    for lemma in PROFANITY[lang]:
        if lemma in rows:
            assert rows[lemma], lemma


@pytest.mark.parametrize("lang", LANGS)
def test_unflagged_examples_do_not_use_flagged_words(lang):
    rows = _rows(lang)
    flagged = {r.lemma for r in rows if r.content_flags}
    for r in rows:
        if r.content_flags or not r.example:
            continue
        hits = [w for w in flagged if re.search(rf"(?<!\w){re.escape(w)}(?!\w)", r.example, re.I)]
        assert hits == [], f"{r.lemma}: example uses flagged {hits}"
