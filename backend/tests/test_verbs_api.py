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
    assert by["fahren"]["forms"]["du"] == {"stem": "fähr", "ending": "st", "changed": True}
    assert by["aufstehen"]["prefix"] == "auf" and by["aufstehen"]["features"] == ["separable"]
