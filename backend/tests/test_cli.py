from pathlib import Path

import pytest

from app.cli import BlacklistRow, LexiconRow, RowError, check_lexicon_uniqueness, read_rows
from app.domain.enums import CefrLevel, Language, frequency_band

DATA = Path(__file__).resolve().parents[1] / "data"


@pytest.mark.parametrize("path", sorted((DATA / "lexicon").glob("*.csv")), ids=lambda p: p.name)
def test_sample_lexicon_files_valid(path):
    rows = read_rows(path, LexiconRow)
    assert rows
    check_lexicon_uniqueness(rows)


def test_default_blacklist_valid():
    assert read_rows(DATA / "blacklist" / "default.csv", BlacklistRow)


def test_lexicon_row_normalisation():
    row = LexiconRow.model_validate(
        {
            "language": "de",
            "rank": "150",
            "lemma": " Haus ",
            "pos": "noun",
            "translation_cs": "dům",
            "ipa": "",
            "cefr": "A1",
            "gender": "das",
            "example": "",
        }
    )
    db = row.to_db()
    assert db["lemma"] == "Haus" and db["pos"] == "NOUN" and db["ipa"] is None
    assert db["frequency_band"] == 500 and db["cefr_level"] is CefrLevel.A1
    assert db["language"] is Language.DE


def test_invalid_rows_collected(tmp_path):
    f = tmp_path / "bad.csv"
    f.write_text(
        "# comment\nlanguage,rank,lemma,pos,translation_cs\nde,2501,x,,y\nes,1,x,,y\nde,1,,,y\n",
        encoding="utf-8",
    )
    with pytest.raises(RowError) as exc:
        read_rows(f, LexiconRow)
    assert len(str(exc.value).splitlines()) == 3


def test_duplicate_rank_rejected():
    rows = [
        LexiconRow(language="de", rank=1, lemma="a", translation_cs="x"),
        LexiconRow(language="de", rank=1, lemma="b", translation_cs="y"),
        LexiconRow(language="fr", rank=1, lemma="a", translation_cs="x"),
    ]
    with pytest.raises(RowError, match="duplicate rank 1 for de"):
        check_lexicon_uniqueness(rows)


def test_invalid_regex_rejected():
    with pytest.raises(ValueError, match="invalid regex"):
        BlacklistRow(pattern_type="regex", pattern="(unclosed", category="violence")


def test_blank_language_means_all():
    assert (
        BlacklistRow.model_validate(
            {"language": "", "pattern_type": "keyword", "pattern": "x", "category": "adult"}
        ).language
        is None
    )


@pytest.mark.parametrize(
    ("rank", "band"), [(1, 100), (100, 100), (101, 500), (1000, 1000), (2001, 2500), (2500, 2500)]
)
def test_frequency_band(rank, band):
    assert frequency_band(rank) == band


@pytest.mark.parametrize("rank", [0, 2501])
def test_frequency_band_out_of_range(rank):
    with pytest.raises(ValueError):
        frequency_band(rank)
