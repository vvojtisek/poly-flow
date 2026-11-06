"""Word export: the learner's own words as a spreadsheet CSV or an Anki import file."""

import csv
import io

from app.domain.export import Row, front, to_anki, to_csv
from tests.helpers import csrf
from tests.test_learning import child_session, run_lesson
from tests.test_scenes import overrides, seed  # noqa: F401  (fixture and seed data)
from tests.test_word_notes import item_id


def _row(**kw) -> Row:
    base = dict(
        lemma="Hund",
        article="der",
        translation="pes",
        status="learning",
        pos="NOUN",
        rank=1,
        example=None,
        note=None,
        next_review="2026-11-07",
        correct=1,
        errors=0,
        source="claude-drafted",
    )
    return Row(**{**base, **kw})


def test_csv_guards_formulas_and_keeps_accents():
    text = to_csv([_row(note="=HYPERLINK(1)"), _row(lemma="Mädchen", translation="-holka")])
    assert text.startswith("﻿")
    rows = list(csv.reader(io.StringIO(text.lstrip("﻿"))))
    assert rows[0][0] == "lemma" and rows[0][-1] == "source"
    assert rows[1][7] == "'=HYPERLINK(1)"
    assert rows[2][0] == "Mädchen" and rows[2][2] == "'-holka"


def test_anki_has_headers_flat_fields_and_tags():
    text = to_anki([_row(note="pes\tštěká\nhlasitě"), _row(article=None, lemma="gut")], "de")
    lines = text.splitlines()
    assert lines[:3] == ["#separator:tab", "#html:false", "#tags column:3"]
    f, b, tags = lines[3].split("\t")
    assert f == "der Hund" and b == "pes (pes štěká hlasitě)"
    assert tags == "polyflow::de polyflow::learning polyflow::source::claude-drafted"
    assert lines[4].split("\t")[0] == "gut" == front(_row(article=None, lemma="gut"))


async def test_export_endpoint_lists_own_met_words(db, client):
    await seed()
    me = await child_session(client)
    empty = await client.get("/api/v1/words/export", params={"language": "de"})
    assert empty.status_code == 200
    assert empty.text.lstrip("﻿").strip().count("\n") == 0  # header only
    await run_lesson(client, me)
    ich = await item_id("ich")
    await client.put(f"/api/v1/words/{ich}/note", json={"text": "+jako já"}, headers=csrf(me))
    r = await client.get("/api/v1/words/export", params={"language": "de"})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert 'filename="polyflow-de-words.csv"' in r.headers["content-disposition"]
    rows = list(csv.reader(io.StringIO(r.text.lstrip("﻿"))))
    by = {row[0]: row for row in rows[1:]}
    assert "ich" in by and by["ich"][7] == "'+jako já"
    anki = await client.get("/api/v1/words/export", params={"language": "de", "format": "anki"})
    assert anki.status_code == 200 and anki.text.startswith("#separator:tab")
    assert len(anki.text.splitlines()) == len(rows) - 1 + 3
    bad = await client.get("/api/v1/words/export", params={"format": "xlsx"})
    assert bad.status_code == 422


async def test_export_requires_login(db, client):
    r = await client.get("/api/v1/words/export")
    assert r.status_code == 401
