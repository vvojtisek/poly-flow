"""C1 review packs preserve the base lexicon and stay outside automatic imports."""

import csv
import json
from pathlib import Path

import pytest

from app.cli import LexiconRow, read_rows
from app.domain.enums import CefrLevel, Language
from app.domain.voices import TOPICS

DATA = Path(__file__).resolve().parents[1] / "data"
LANGUAGES = ("de", "en", "fr", "it")


def base_rows(language):
    return [
        r
        for path in (DATA / "lexicon").glob(f"{language}.*.csv")
        for r in read_rows(path, LexiconRow)
    ]


@pytest.mark.parametrize("language", LANGUAGES)
def test_complete_c1_draft_has_unique_new_keys_and_explicit_provenance(language):
    rows = read_rows(DATA / "c1" / f"{language}.5001-8000.csv", LexiconRow)
    assert [r.rank for r in rows] == list(range(5001, 8001))
    assert len({r.lemma.casefold() for r in rows}) == 3000
    existing = {r.lemma.casefold() for r in base_rows(language)}
    assert existing.isdisjoint(r.lemma.casefold() for r in rows)
    assert all(r.language == Language(language) and r.cefr is CefrLevel.C1 for r in rows)
    assert all(r.source == "wikdict-wordfreq-unreviewed" for r in rows)
    assert all(r.license == "CC-BY-SA-4.0" and r.revision == "c1-candidates-v1" for r in rows)
    assert all(r.example is None and r.ipa is None for r in rows)
    assert all(len(r.translation_cs) <= 255 and len(r.lemma) <= 128 for r in rows)
    if language != "en":
        genders = {"der", "die", "das"} if language == "de" else {"m", "f"}
        assert all(r.gender in genders for r in rows if r.pos == "NOUN")
    # Bad source pairs found during discovery must never reappear as learning candidates.
    if language == "it":
        assert {"mettersi", "salvatore", "trovato"}.isdisjoint(r.lemma for r in rows)


def test_interest_packs_have_parity_resolvable_keys_and_safe_rank_reuse():
    manifest = json.loads((DATA / "specialized/topics.json").read_text())
    topics = manifest["topics"]
    assert len(topics) == 14
    assert set(topics) <= set(TOPICS)
    assert manifest["review_status"] == "unreviewed"
    for language in LANGUAGES:
        base = base_rows(language)
        c1 = read_rows(DATA / "c1" / f"{language}.5001-8000.csv", LexiconRow)
        specialist = read_rows(DATA / "specialized" / f"{language}.interests.csv", LexiconRow)
        rows = [*base, *c1, *specialist]
        assert len({r.rank for r in rows}) == len(rows)
        assert len({(r.lemma, r.pos) for r in rows}) == len(rows)
        earlier = {r.lemma.casefold() for r in [*base, *c1]}
        assert earlier.isdisjoint(r.lemma.casefold() for r in specialist)
        assert [r.rank for r in specialist] == list(range(8001, 8001 + len(specialist)))
        assert all(r.cefr is None and r.source == "codex-drafted-unreviewed" for r in specialist)
        indexed = {(r.lemma, r.pos, r.rank): r for r in rows}
        for topic, translations in topics.items():
            assert set(translations) == set(LANGUAGES)
            assert len(translations[language]) == 5
            for term in translations[language]:
                key = term["lemma"], term["pos"], term["rank"]
                assert key in indexed
                assert term["translation_cs"] and term["review_status"] == "unreviewed"
                if topic == "criminology":
                    assert "violence" in term["content_flags"]
        for row in specialist:
            if "violence" in row.content_flags:
                assert row.rank > 8000


@pytest.mark.parametrize("language", LANGUAGES)
def test_drafts_do_not_change_default_imports(language):
    rows = base_rows(language)
    assert len(rows) == 5000
    assert max(r.rank for r in rows) == 5000
    with (DATA / "c1" / f"{language}.5001-8000.csv").open() as handle:
        headers = csv.DictReader(x for x in handle if not x.startswith("#")).fieldnames
    assert "content_flags" in headers and "translation_cs" in headers
