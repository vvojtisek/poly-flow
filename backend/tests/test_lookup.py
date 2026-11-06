import pytest

from app.api.deps import get_limiter
from app.cli import LexiconRow, upsert_lexicon
from app.domain.lookup import candidates, clean
from app.main import app
from app.services.rate_limit import MemoryAttemptLimiter
from tests.helpers import setup_parent
from tests.test_learning import child_session


@pytest.mark.parametrize(
    ("word", "language", "lemma"),
    [
        ("Kinder", "de", "kind"),
        ("Städte", "de", "stadt"),
        ("Bücher,", "de", "buch"),
        ("Freundinnen", "de", "freundin"),
        ("ist", "de", "sein"),
        ("running", "en", "run"),
        ("stopped", "en", "stop"),
        ("cities", "en", "city"),
        ("went", "en", "go"),
        ("children", "en", "child"),
        ("l'homme", "fr", "homme"),
        ("chevaux", "fr", "cheval"),
        ("parlons", "fr", "parler"),
        ("ragazzi", "it", "ragazzo"),
        ("dell\u2019acqua", "it", "acqua"),
        ("parliamo", "it", "parlare"),
    ],
)
def test_candidates_include_lemma(word, language, lemma):
    assert lemma in candidates(word, language)


def test_candidates_order_and_cleaning():
    assert candidates("Haus", "de")[0] == "haus"  # the word itself first
    assert clean("  «Hallo!»  ") == "hallo"
    assert clean("123 !!") == ""
    assert candidates("...", "de") == []
    c = candidates("Kinder", "de")
    assert len(c) == len(set(c))


@pytest.fixture(autouse=True)
def limiter():
    app.dependency_overrides[get_limiter] = lambda: MemoryAttemptLimiter()
    yield
    app.dependency_overrides.clear()


async def _seed():
    await upsert_lexicon(
        [
            LexiconRow(language="de", rank=1, lemma="geben", pos="VERB", translation_cs="dát"),
            LexiconRow(
                language="de", rank=2, lemma="Kind", pos="NOUN", translation_cs="dítě", gender="das"
            ),
            LexiconRow(language="de", rank=5, lemma="heiß", pos="ADJ", translation_cs="horký"),
            LexiconRow(
                language="de", rank=6, lemma="heißen", pos="VERB", translation_cs="jmenovat se"
            ),
            LexiconRow(
                language="de", rank=3, lemma="aufstehen", pos="VERB", translation_cs="vstát"
            ),
            LexiconRow(
                language="de",
                rank=4,
                lemma="töten",
                pos="VERB",
                translation_cs="zabít",
                content_flags=["violence"],
            ),
        ]
    )


async def test_lookup_finds_forms(db, client):
    await setup_parent(client)
    await _seed()
    hits = (await client.get("/api/v1/lookup", params={"word": "Kinder", "language": "de"})).json()
    assert [h["lemma"] for h in hits] == ["Kind"]
    assert hits[0]["gender"] == "das" and hits[0]["translation"] == "dítě"
    assert hits[0]["status"] is None  # not met yet; nothing is recorded by looking up
    gibt = (await client.get("/api/v1/lookup", params={"word": "gibt", "language": "de"})).json()
    assert [h["lemma"] for h in gibt] == ["geben"]
    stehe = (await client.get("/api/v1/lookup", params={"word": "stehe", "language": "de"})).json()
    assert [h["lemma"] for h in stehe] == ["aufstehen"]
    adult = (await client.get("/api/v1/lookup", params={"word": "tötet"})).json()
    assert [h["lemma"] for h in adult] == ["töten"]  # the child test below relies on this
    heisse = (await client.get("/api/v1/lookup", params={"word": "heiße"})).json()
    assert [h["lemma"] for h in heisse] == ["heißen", "heiß"]  # exact verb form first
    none = (await client.get("/api/v1/lookup", params={"word": "Zebra", "language": "de"})).json()
    assert none == []
    bad = await client.get("/api/v1/lookup", params={"word": "", "language": "de"})
    assert bad.status_code == 422


async def test_lookup_respects_child_filter(db, client):
    await child_session(client)
    await _seed()
    r = await client.get("/api/v1/lookup", params={"word": "tötet", "language": "de"})
    assert r.status_code == 200 and r.json() == []


async def test_lookup_requires_login(db, client):
    r = await client.get("/api/v1/lookup", params={"word": "Kind"})
    assert r.status_code == 401
