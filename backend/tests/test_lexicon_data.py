"""The committed English lexicon (core-100 + ranks 101-1000): shape, order, safety, and gates."""

import csv
import re
from pathlib import Path

import pytest

from app.cli import LexiconRow, read_rows, upsert_lexicon
from app.domain.enums import CefrLevel
from app.domain.level_exam import BY_LEVEL, band_complete
from tests.helpers import login, make_child, setup_parent
from tests.test_learning import overrides  # noqa: F401  (fixture)

DATA = Path(__file__).resolve().parents[1] / "data"
EN_FILES = sorted((DATA / "lexicon").glob("en.*.csv"))


def _en() -> list[LexiconRow]:
    return [r for p in EN_FILES for r in read_rows(p, LexiconRow)]


def _gb() -> dict[str, tuple[int, set[str]]]:
    with (DATA / "frequency" / "en_GB.lemmas.csv").open(encoding="utf-8") as fh:
        rows = csv.DictReader(x for x in fh if not x.startswith("#"))
        return {
            r["lemma"]: (int(r["rank"]), set(filter(None, r["content_flags"].split("|"))))
            for r in rows
        }


def _word(lemma: str):
    return re.compile(rf"(?<!\w){re.escape(lemma)}(?!\w)", re.IGNORECASE)


def test_ranks_run_1_to_1000_without_gaps():
    rows = _en()
    assert sorted(r.rank for r in rows) == list(range(1, 1001))
    lemmas = [r.lemma.lower() for r in rows]
    assert len(set(lemmas)) == len(lemmas)


def test_a1_and_a2_bands_count_as_imported():
    ranks = [r.rank for r in _en()]
    for level in (CefrLevel.A1, CefrLevel.A2):
        band = BY_LEVEL[level]
        assert band_complete(band, sum(band.low < r <= band.high for r in ranks))
    b1 = BY_LEVEL[CefrLevel.B1]
    assert not band_complete(b1, sum(b1.low < r <= b1.high for r in ranks))


def test_glosses_are_unique():
    """Recall shows the Czech gloss and expects one lemma: two words may not share a gloss."""
    glosses = [r.translation_cs for r in _en()]
    dupes = sorted({g for g in glosses if glosses.count(g) > 1})
    assert dupes == []


def test_block_above_core_follows_the_en_gb_frequency_list():
    gb = _gb()
    block = sorted((r for r in _en() if r.rank > 100), key=lambda r: r.rank)
    aliases = {"according to": "according", "per cent": "percent"}
    gb_ranks = [gb[aliases.get(r.lemma, r.lemma.lower())][0] for r in block]
    assert gb_ranks == sorted(gb_ranks)
    # Drafts are marked as such until a native speaker has reviewed them.
    assert {(r.source, r.license, r.revision) for r in block} == {
        ("claude-drafted", "CC-BY-SA-4.0", "en1000-draft-v1")
    }
    assert all(r.example for r in block)  # lessons without a scene show the example
    with_cloze = sum(bool(_word(r.lemma).search(r.example)) for r in block)
    assert with_cloze >= 0.95 * len(block)


def test_content_flags_carry_over_and_examples_stay_clean():
    gb = _gb()
    rows = _en()
    for r in rows:
        listed = gb.get(r.lemma.lower(), (0, set()))[1]
        assert listed <= {f.value for f in r.content_flags}, r.lemma
    flagged = {lemma for lemma, (_, flags) in gb.items() if flags}
    for r in rows:
        if r.content_flags or not r.example:
            continue  # flagged items never reach child profiles, examples included
        hits = [w for w in flagged if _word(w).search(r.example)]
        assert hits == [], f"{r.lemma}: example uses flagged {hits}"


# ---------------------------------------------------------------- database


@pytest.fixture
async def english(db):
    await upsert_lexicon(_en())


async def test_placement_and_exams_see_the_whole_lexicon(english, client):
    await setup_parent(client)
    r = await client.get("/api/v1/learning/placement?language=en")
    assert r.status_code == 200, r.text
    assert r.json()["ceiling"] == 1000
    r = await client.get("/api/v1/learning/levels?language=en")
    assert r.status_code == 200, r.text
    levels = {lv["level"]: lv for lv in r.json()["levels"]}
    assert levels["A1"]["state"] == "not_ready" and levels["A1"]["lexicon_items"] == 500
    assert levels["A2"]["state"] == "needs_previous" and levels["A2"]["lexicon_items"] == 500
    assert levels["B1"]["state"] == "missing_words"


async def test_child_pool_leaves_out_flagged_words(english, client, overrides):  # noqa: F811
    parent = await setup_parent(client)
    await make_child(client, parent)
    await login(client, "eva", "4321")
    r = await client.get("/api/v1/learning/levels?language=en")
    assert r.status_code == 200, r.text
    levels = {lv["level"]: lv for lv in r.json()["levels"]}
    flagged = sum(1 for row in _en() if row.content_flags and row.rank <= 1000)
    assert levels["A1"]["pool"] + levels["A2"]["pool"] == 1000 - flagged
    assert flagged > 0
