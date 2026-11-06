"""Spelling-to-sound guide: rule matches, highlight spans and the API with the child filter."""

import pytest

from app.cli import LexiconRow, upsert_lexicon
from app.domain.sounds import RULES, rules
from tests.helpers import setup_parent
from tests.test_learning import child_session


def _rule(language, rid):
    return next(r for r in rules(language) if r.id == rid)


@pytest.mark.parametrize(
    ("language", "rid", "word", "part"),
    [
        ("de", "ei", "mein", "ei"),
        ("de", "eu", "heute", "eu"),
        ("de", "sch", "schule", "sch"),
        ("de", "tsch", "deutsch", "tsch"),
        ("de", "st", "stadt", "st"),
        ("de", "ch_hard", "buch", "ch"),
        ("de", "ch_soft", "ich", "ch"),
        ("de", "ch_soft", "euch", "ch"),
        ("de", "z", "jetzt", "tz"),
        ("fr", "oi", "moi", "oi"),
        ("fr", "au", "beaucoup", "eau"),
        ("fr", "in", "bien", "ien"),
        ("fr", "j", "manger", "g"),
        ("fr", "c", "merci", "c"),
        ("it", "ce", "cena", "c"),
        ("it", "che", "anche", "ch"),
        ("it", "double", "piccolo", "cc"),
        ("en", "th", "think", "th"),
        ("en", "igh", "night", "igh"),
        ("en", "tion", "nation", "tion"),
    ],
)
def test_rule_matches(language, rid, word, part):
    span = _rule(language, rid).find(word)
    assert span is not None and word[span[0] : span[1]] == part


@pytest.mark.parametrize(
    ("language", "rid", "word"),
    [
        ("de", "ch_hard", "euch"),  # soft after eu
        ("de", "ch_soft", "schule"),  # sch is not ch
        ("de", "ch_soft", "sechs"),  # chs reads ks
        ("de", "sch", "deutsch"),  # tsch is its own rule
        ("de", "eu", "museum"),
        ("fr", "u", "un"),  # nasal, not ü
        ("fr", "an", "bien"),  # ien is nasal e
        ("fr", "ill", "ville"),  # the known exception
        ("it", "ce", "scena"),  # sc + e is š
        ("en", "w", "who"),
        ("en", "ch", "school"),
        ("en", "ee", "year"),
        ("en", "oo", "book"),
        ("en", "e", "the"),
        ("en", "y", "my"),
        ("en", "r", "tomorrow"),
    ],
)
def test_rule_exceptions_do_not_match(language, rid, word):
    assert _rule(language, rid).find(word) is None


def test_every_rule_is_well_formed():
    for language, rs in RULES.items():
        assert len({r.id for r in rs}) == len(rs), language
        for r in rs:
            assert r.spelling and r.czech and r.note


async def test_sounds_api(db, client):
    await setup_parent(client)
    await upsert_lexicon(
        [
            LexiconRow(language="de", rank=1, lemma="mein", pos="DET", translation_cs="můj"),
            LexiconRow(language="de", rank=2, lemma="heute", pos="ADV", translation_cs="dnes"),
        ]
    )
    out = (await client.get("/api/v1/sounds", params={"language": "de"})).json()
    by = {r["id"]: r for r in out}
    assert [r["id"] for r in out] == [r.id for r in rules("de")]
    ex = by["ei"]["examples"]
    assert ex == [
        {
            "id": ex[0]["id"],
            "lemma": "mein",
            "translation": "můj",
            "start": 1,
            "end": 3,
            "met": False,
        }
    ]
    assert by["tsch"]["examples"] == []


async def test_sounds_child_filter(db, client):
    await child_session(client)
    await upsert_lexicon(
        [
            LexiconRow(
                language="de",
                rank=1,
                lemma="Scheiße",
                pos="NOUN",
                translation_cs="hovno",
                content_flags=["profanity"],
            ),
        ]
    )
    out = (await client.get("/api/v1/sounds", params={"language": "de"})).json()
    assert all(e["lemma"] != "Scheiße" for r in out for e in r["examples"])
