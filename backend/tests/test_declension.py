"""German case lab API: paradigm plus nouns and adjectives from the lexicon."""

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


def row(rank, lemma, pos, cs, gender=None, flags=()):
    return LexiconRow(
        language="de",
        rank=rank,
        lemma=lemma,
        pos=pos,
        translation_cs=cs,
        gender=gender,
        content_flags=list(flags),
    )


async def test_declension_lab(db, client):
    await setup_parent(client)
    await upsert_lexicon(
        [
            row(1, "Kind", "NOUN", "dítě", "das"),
            row(2, "Junge", "NOUN", "chlapec", "der"),
            row(3, "Eltern", "NOUN", "rodiče", "die"),
            row(4, "Erwachsene", "NOUN", "dospělý", "der"),
            row(5, "klein", "ADJ", "malý"),
            row(6, "lila", "ADJ", "fialový"),
            row(7, "gehen", "VERB", "jít"),
        ]
    )
    r = await client.get("/api/v1/grammar/declension")
    assert r.status_code == 200
    out = r.json()
    assert len(out["cells"]) == 5 * 4 * 4
    cell = next(
        c for c in out["cells"] if (c["det"], c["case"], c["gender"]) == ("indef", "nom", "m")
    )
    assert cell["determiner"] == {"stem": "ein", "ending": ""}
    assert cell["adjective_ending"] == "er" and cell["signal"] == "adjective"
    nouns = {n["lemma"]: n for n in out["nouns"]}
    assert "Erwachsene" not in nouns  # adjectival noun: declines like an adjective
    assert nouns["Junge"]["n_declension"] and nouns["Junge"]["singular"]["dat"]["ending"] == "n"
    assert nouns["Kind"]["plural"]["dat"] == {"stem": "Kinder", "ending": "n"}
    assert nouns["Eltern"]["gender"] == "pl" and nouns["Eltern"]["singular"] is None
    adjectives = {a["lemma"]: a["stem"] for a in out["adjectives"]}
    assert adjectives == {"klein": "klein", "lila": None}


async def test_declension_requires_login(db, client):
    assert (await client.get("/api/v1/grammar/declension")).status_code == 401
