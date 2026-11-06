"""Minimal pairs: the data is well formed and the API serves only its own words."""

from app.domain.minimal_pairs import SETS, find
from tests.helpers import setup_parent


def test_sets_are_well_formed():
    for language, sets in SETS.items():
        assert sets, language
        assert len({s.id for s in sets}) == len(sets)
        for s in sets:
            assert s.title and s.hint and len(s.pairs) >= 2, s.id
            for a, b in s.pairs:
                assert a.text != b.text and a.cs and b.cs
                assert " " not in a.text and " " not in b.text  # single words


def test_find():
    assert find("it", "double").pairs[0][1].text == "palla"
    assert find("it", "nope") is None and find("de", "double") is None


async def test_pairs_api(db, client):
    await setup_parent(client)
    out = (await client.get("/api/v1/pairs", params={"language": "en"})).json()
    th = next(s for s in out if s["id"] == "th")
    assert th["pairs"][0] == [{"text": "think", "cs": "myslet"}, {"text": "sink", "cs": "dřez"}]
    missing = await client.get(
        "/api/v1/pairs/audio", params={"language": "en", "set": "th", "pair": 40, "side": 0}
    )
    assert missing.status_code == 404
    bad = await client.get(
        "/api/v1/pairs/audio", params={"language": "en", "set": "th", "pair": 0, "side": 2}
    )
    assert bad.status_code == 422


async def test_pairs_require_login(db, client):
    assert (await client.get("/api/v1/pairs")).status_code == 401
