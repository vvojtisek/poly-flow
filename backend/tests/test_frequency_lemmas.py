"""The committed English frequency lists and their import (data/frequency, `seed-lemmas`)."""

import csv
from pathlib import Path

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from app.cli import (
    FrequencyLemmaRow,
    RowError,
    _seed_lemmas,
    check_lemma_list,
    lemma_file_locale,
    read_rows,
    upsert_lemmas,
)
from app.db.session import get_session
from app.domain.lemmas import is_valid_lemma
from app.domain.progression import frequency_band
from app.models import FrequencyLemma

DATA = Path(__file__).resolve().parents[1] / "data"
EN_GB = DATA / "frequency" / "en_GB.lemmas.csv"
EN_US = DATA / "frequency" / "en_US.lemmas.csv"
UPOS = {
    "ADJ", "ADP", "ADV", "AUX", "CCONJ", "DET", "INTJ", "NOUN", "NUM", "PART", "PRON",
    "PROPN", "SCONJ", "VERB", "X",
}  # fmt: skip
# Spelling variants: each list holds its own form and not the other one.
SPELLING = {
    "en_GB": {"colour", "centre", "realise", "organisation", "jewellery"},
    "en_US": {"color", "center", "realize", "organization", "jewelry"},
}


@pytest.fixture(scope="module", params=[EN_GB, EN_US], ids=lambda p: p.name)
def lemma_file(request) -> tuple[str, list[FrequencyLemmaRow]]:
    return lemma_file_locale(request.param), read_rows(request.param, FrequencyLemmaRow)


def row(rank: int, lemma: str, flags: str = "") -> FrequencyLemmaRow:
    return FrequencyLemmaRow(
        rank=rank, lemma=lemma, content_flags=flags, source="test", license="CC0-1.0", revision="t"
    )


# --- the committed files -------------------------------------------------------------------


def test_exactly_10000_unique_ranked_lemmas(lemma_file):
    _, rows = lemma_file
    assert len(rows) == 10_000
    assert len({r.lemma for r in rows}) == 10_000
    assert [r.rank for r in rows] == list(range(1, 10_001))
    check_lemma_list(rows)


def test_lemmas_are_normalised(lemma_file):
    _, rows = lemma_file
    assert all(is_valid_lemma(r.lemma) for r in rows)
    assert {r.lemma for r in rows if len(r.lemma) == 1} == {"a", "i"}
    assert {r.pos for r in rows} <= UPOS | {None}
    assert all(r.source and r.license and r.revision for r in rows)


def test_lemmas_not_word_forms_or_names(lemma_file):
    _, rows = lemma_file
    lemmas = {r.lemma for r in rows}
    assert {"be", "have", "go", "run", "child", "good", "see"} <= lemmas
    assert not {"was", "ran", "running", "children", "london", "tv", "york", "simon"} & lemmas


def test_spelling_follows_the_locale(lemma_file):
    locale, rows = lemma_file
    lemmas = {r.lemma for r in rows}
    other = next(k for k in SPELLING if k != locale)
    assert SPELLING[locale] <= lemmas
    assert not SPELLING[other] & lemmas


def test_british_list_uses_british_words():
    lemmas = {r.lemma for r in read_rows(EN_GB, FrequencyLemmaRow)}
    assert {"mum", "maths", "tire", "program"} <= lemmas
    assert not {"mom", "math", "sidewalk"} & lemmas


def test_flags_reach_the_child_filter(lemma_file):
    _, rows = lemma_file
    flags = {r.lemma: {f.value for f in r.content_flags} for r in rows}
    assert flags["fuck"] == {"profanity"} and flags["kill"] == {"violence"}
    assert flags["porn"] == {"sexual"} and flags["dog"] == set()


def test_english_core100_is_inside_the_list(lemma_file):
    _, rows = lemma_file
    ranks = {r.lemma: r.rank for r in rows}
    with (DATA / "lexicon" / "en.core100.csv").open(encoding="utf-8") as fh:
        core = [r["lemma"] for r in csv.DictReader(x for x in fh if not x.startswith("#"))]
    assert len(core) == 100
    assert all(ranks.get(lemma.lower(), 10_001) <= 1000 for lemma in core if lemma != "cat")


# --- validation ----------------------------------------------------------------------------


@pytest.mark.parametrize("bad", ["Run", "café", "x", "u.s", "2nd", "don't", "-ish", "a--b"])
def test_unnormalised_lemma_rejected(bad):
    with pytest.raises(ValueError):
        row(1, bad)


def test_duplicates_and_rank_gaps_rejected():
    with pytest.raises(RowError, match="duplicate lemmas: go"):
        check_lemma_list([row(1, "go"), row(2, "go")])
    with pytest.raises(RowError, match=r"exactly 1\.\.2"):
        check_lemma_list([row(1, "go"), row(3, "be")])


@pytest.mark.parametrize("name", ["en_US.csv", "english.lemmas.csv", "en-us.lemmas.csv"])
def test_file_name_must_carry_the_locale(name):
    with pytest.raises(RowError):
        lemma_file_locale(Path(name))


# --- database ------------------------------------------------------------------------------


async def _snapshot(locale: str = "en_US") -> dict[str, tuple]:
    async for s in get_session():
        rows = (
            (await s.execute(select(FrequencyLemma).where(FrequencyLemma.locale == locale)))
            .scalars()
            .all()
        )
        return {r.lemma: (r.id, r.rank, r.frequency_band, tuple(r.content_flags)) for r in rows}


async def test_seed_command_is_idempotent(db):
    assert await _seed_lemmas([EN_GB, EN_US], dry_run=False) == 0
    first = {locale: await _snapshot(locale) for locale in ("en_GB", "en_US")}
    for snapshot in first.values():
        assert len(snapshot) == 10_000
        assert sorted(v[1] for v in snapshot.values()) == list(range(1, 10_001))
        assert snapshot["the"][1:3] == (1, frequency_band(1))
        assert snapshot["fuck"][3] == ("profanity",)
    assert "colour" in first["en_GB"] and "color" in first["en_US"]

    assert await _seed_lemmas([EN_GB, EN_US], dry_run=False) == 0
    assert {locale: await _snapshot(locale) for locale in first} == first  # same ids


async def test_reimport_replaces_list_and_only_adds_flags(db):
    await upsert_lemmas("en_US", [row(1, "go", "violence"), row(2, "be"), row(3, "old")])
    await upsert_lemmas("en_US", [row(1, "be"), row(2, "go"), row(3, "new")])
    after = await _snapshot()
    assert {k: v[1] for k, v in after.items()} == {"be": 1, "go": 2, "new": 3}
    assert after["go"][3] == ("violence",)


async def test_dry_run_writes_nothing(db):
    assert await _seed_lemmas([EN_GB, EN_US], dry_run=True) == 0
    assert await _snapshot("en_GB") == {} and await _snapshot("en_US") == {}


async def _insert(values: str) -> None:
    async for s in get_session():
        async with s.begin():
            await s.execute(
                text(
                    "INSERT INTO frequency_lemmas (id, locale, lemma, rank, frequency_band,"
                    " source, license, revision) SELECT gen_random_uuid(), v.*, 's', 'l', 'r'"
                    f" FROM (VALUES {values}) AS v"
                )
            )


@pytest.mark.parametrize(
    "values",
    [
        "('en_US', NULL, 1, 100)",
        "('en_US', 'Run', 1, 100)",
        "('english', 'run', 1, 100)",
        "('en_US', 'run', 0, 100)",
        "('en_US', 'go', 2, 100)",  # duplicate (locale, lemma)
        "('en_US', 'run', 1, 100)",  # duplicate (locale, rank), checked at commit
    ],
)
async def test_schema_constraints(db, values):
    await upsert_lemmas("en_US", [row(1, "go")])
    await _insert("('de_DE', 'go', 1, 100)")  # control: the statement itself is valid
    with pytest.raises(IntegrityError):
        await _insert(values)


async def test_lookup_uses_the_unique_index(db):
    assert await _seed_lemmas([EN_GB, EN_US], dry_run=False) == 0
    async for s in get_session():
        await s.execute(text("ANALYZE frequency_lemmas"))
        plan = "\n".join(
            (
                await s.execute(
                    text(
                        "EXPLAIN SELECT 1 FROM frequency_lemmas"
                        " WHERE locale = 'en_GB' AND lemma = 'develop'"
                    )
                )
            ).scalars()
        )
    assert "Index Only Scan using uq_frequency_lemmas_locale_lemma" in plan, plan
