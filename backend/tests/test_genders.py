"""Gender sorter API."""

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


def noun(lang, rank, lemma, gender, cs="x", flags=()):
    return LexiconRow(
        language=lang,
        rank=rank,
        lemma=lemma,
        pos="NOUN",
        translation_cs=cs,
        gender=gender,
        content_flags=list(flags),
    )


async def test_gender_sorter(db, client):
    await setup_parent(client)
    await upsert_lexicon(
        [
            noun("de", 1, "Zeitung", "die", "noviny"),
            noun("de", 2, "Junge", "der", "chlapec"),
            noun("de", 3, "Tisch", "der", "stůl"),
            noun("fr", 1, "enfant", "m/f", "dítě"),
            noun("fr", 2, "question", "f", "otázka"),
        ]
    )
    out = (await client.get("/api/v1/genders?language=de")).json()
    assert out["genders"] == ["der", "die", "das"]
    by = {n["lemma"]: n for n in out["nouns"]}
    assert by["Zeitung"]["hint"] == {
        "suffix": "ung",
        "gender": "die",
        "certainty": "always",
        "exception": False,
    }
    assert by["Junge"]["hint"]["exception"] is True
    assert by["Tisch"]["hint"] is None
    assert any(r["suffix"] == "ung" for r in out["rules"])
    fr = (await client.get("/api/v1/genders?language=fr")).json()
    assert [n["lemma"] for n in fr["nouns"]] == ["question"]  # m/f has no single answer
    r = await client.get("/api/v1/genders?language=en")
    assert r.status_code == 404
