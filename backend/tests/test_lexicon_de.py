"""The committed German lexicon (core-100 + drafted ranks 101-1000): shape, provenance, gates."""

import re
from pathlib import Path

from app.cli import LexiconRow, read_rows
from app.domain.enums import CefrLevel
from app.domain.level_exam import BY_LEVEL, band_complete

DATA = Path(__file__).resolve().parents[1] / "data" / "lexicon"
DE_FILES = sorted(DATA.glob("de.*.csv"))
ARTICLES = {"der", "die", "das"}


def _de() -> list[LexiconRow]:
    return [r for p in DE_FILES for r in read_rows(p, LexiconRow)]


def test_ranks_run_1_to_1000_and_keys_are_unique():
    rows = _de()
    assert sorted(r.rank for r in rows) == list(range(1, 1001))
    keys = [(r.lemma, r.pos) for r in rows]
    assert len(set(keys)) == len(keys)


def test_a1_and_a2_bands_count_as_imported():
    ranks = [r.rank for r in _de()]
    for level in (CefrLevel.A1, CefrLevel.A2):
        band = BY_LEVEL[level]
        assert band_complete(band, sum(band.low < r <= band.high for r in ranks))


def test_glosses_are_unique():
    """Recall shows the Czech gloss and expects one lemma: two words may not share a gloss."""
    glosses = [r.translation_cs for r in _de()]
    assert sorted({g for g in glosses if glosses.count(g) > 1}) == []


def test_drafted_block_is_marked_and_complete():
    drafted = [r for r in _de() if r.rank > 100]
    assert len(drafted) == 900
    for r in drafted:
        assert (r.source, r.license, r.revision) == ("claude-drafted", "CC0-1.0", "de1000-draft-v1")
        assert r.translation_cs and r.example, r.lemma
        assert r.gender in (None, "", *ARTICLES), r.lemma


def test_nouns_are_capitalised_and_gendered():
    for r in _de():
        if r.pos == "NOUN" and r.lemma not in {"Deutsch", "Englisch", "Tschechisch"}:
            assert r.lemma[0].isupper(), r.lemma
            assert r.gender in ARTICLES, r.lemma


def test_examples_are_sentences_in_german():
    for r in _de():
        if r.rank > 100:
            assert re.match(r"^[A-ZÄÖÜ]", r.example), r.lemma
            assert r.example.rstrip()[-1] in ".!?", r.lemma
