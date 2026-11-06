import pytest

from app.api.deps import get_limiter
from app.cli import LexiconRow, upsert_lexicon
from app.main import app
from app.services.rate_limit import MemoryAttemptLimiter
from tests.helpers import setup_parent


@pytest.fixture(autouse=True)
def limiter():
    app.dependency_overrides[get_limiter] = lambda: MemoryAttemptLimiter()
    yield
    app.dependency_overrides.clear()


async def test_verb_lab(db, client):
    await setup_parent(client)
    await upsert_lexicon(
        [
            LexiconRow(language="de", rank=1, lemma="fahren", pos="VERB", translation_cs="jet"),
            LexiconRow(
                language="de", rank=2, lemma="aufstehen", pos="VERB", translation_cs="vstát"
            ),
            LexiconRow(language="de", rank=3, lemma="Haus", pos="NOUN", translation_cs="dům"),
        ]
    )
    out = (await client.get("/api/v1/grammar/verbs")).json()
    by = {v["lemma"]: v for v in out}
    assert set(by) == {"fahren", "aufstehen"}
    assert by["fahren"]["forms"][1] == {
        "pronoun": "du",
        "stem": "fähr",
        "ending": "st",
        "changed": True,
    }
    assert [f["pronoun"] for f in by["fahren"]["forms"]][2] == "er/sie/es"
    assert by["aufstehen"]["prefix"] == "auf" and by["aufstehen"]["features"] == ["separable"]


async def test_verb_lab_french_and_italian(db, client):
    await setup_parent(client)
    await upsert_lexicon(
        [
            LexiconRow(language="fr", rank=1, lemma="manger", pos="VERB", translation_cs="jíst"),
            LexiconRow(language="fr", rank=2, lemma="aimer", pos="VERB", translation_cs="mít rád"),
            LexiconRow(
                language="fr", rank=3, lemma="s'appeler", pos="VERB", translation_cs="jmenovat se"
            ),
            LexiconRow(language="it", rank=1, lemma="cercare", pos="VERB", translation_cs="hledat"),
            LexiconRow(language="de", rank=1, lemma="fahren", pos="VERB", translation_cs="jet"),
        ]
    )
    fr = {v["lemma"]: v for v in (await client.get("/api/v1/grammar/verbs?language=fr")).json()}
    assert set(fr) == {"manger", "aimer"}  # the reflexive entry is left out, German is not mixed in
    assert fr["manger"]["forms"][3] == {
        "pronoun": "nous",
        "stem": "mange",
        "ending": "ons",
        "changed": True,
    }
    assert fr["aimer"]["forms"][0]["pronoun"] == "j'"
    assert fr["aimer"]["prefix"] is None and "elision" in fr["aimer"]["features"]
    it = (await client.get("/api/v1/grammar/verbs?language=it")).json()
    assert [f["stem"] + f["ending"] for f in it[0]["forms"]][1] == "cerchi"
    assert it[0]["features"] == ["it_are", "it_h"]


async def test_verb_lab_rejects_english(db, client):
    await setup_parent(client)
    assert (await client.get("/api/v1/grammar/verbs?language=en")).status_code == 422
