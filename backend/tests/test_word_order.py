"""Word order practice: the pure rules and the API over met scenes and example sentences."""

from app.domain import word_order as wo
from tests.helpers import csrf
from tests.test_learning import child_session, finish, start
from tests.test_scenes import overrides, seed  # noqa: F401  (fixture and seed data)


def test_split_keeps_end_and_inner_punctuation():
    p = wo.split("  Ich bin  Tom. Und du? ")
    assert p.tiles == ["Ich", "bin", "Tom.", "Und", "du"] and p.end == "?"
    assert wo.split("Hallo").end == "" and wo.split("").tiles == []
    assert wo.split("Wirklich…").end == "…"


def test_usable_and_lower_first():
    assert not wo.usable(wo.split("Hallo Anna!"))  # too short
    assert not wo.usable(wo.split("ja ja ja"))  # nothing to order
    assert wo.usable(wo.split("Ich trinke Kaffee."))
    assert not wo.usable(wo.split(" ".join(["a", "b"] * 6)))  # too long
    assert wo.lower_first(wo.split("Ich trinke Kaffee.")).tiles[0] == "ich"


def test_shuffle_is_stable_and_differs():
    tiles = ["ich", "trinke", "Kaffee"]
    a = wo.shuffled(tiles, "ref")
    assert a == wo.shuffled(tiles, "ref") and a != tiles and sorted(a) == sorted(tiles)


def test_marks():
    exp = ["ich", "trinke", "heute", "Kaffee"]
    assert wo.marks(exp, exp) == [True] * 4
    assert wo.marks(exp, ["heute", "trinke", "ich", "Kaffee"]) == [False, True, False, True]
    assert wo.marks(exp, ["ich"]) == [True, False, False, False]
    assert wo.same_words(exp, list(reversed(exp))) and not wo.same_words(exp, exp[:3])


async def test_word_order_api(db, client):
    await seed()
    me = await child_session(client)
    empty = (await client.get("/api/v1/word-order/next?language=de")).json()
    assert empty == {"ref": None, "pool": 0}
    s = await start(client, me)
    await finish(client, me, s)
    seen: dict[str, dict] = {}
    for _ in range(30):
        p = (await client.get("/api/v1/word-order/next?language=de")).json()
        seen[p["ref"]] = p
    scene = next(p for r, p in seen.items() if r.startswith("s:") and p["end"] == "?")
    # The first word lost its capital (a pronoun), the end punctuation is fixed.
    assert sorted(scene["tiles"]) == sorted(["ich", "bin", "Tom.", "Und", "du"])
    assert scene["cs"] and scene["hint"] is None

    async def check(ref, order):
        return await client.post(
            "/api/v1/word-order/check?language=de",
            json={"ref": ref, "order": order},
            headers=csrf(me),
        )

    ok = (await check(scene["ref"], ["ich", "bin", "Tom.", "Und", "du"])).json()
    assert ok["correct"] is True and ok["sentence"] == "Ich bin Tom. Und du?"
    wrong = (await check(scene["ref"], ["bin", "ich", "Tom.", "Und", "du"])).json()
    assert wrong["correct"] is False and wrong["marks"] == [False, False, True, True, True]
    assert (await check(scene["ref"], ["ich", "bin"])).status_code == 422
    assert (await check("s:not-a-uuid:0", ["a"])).status_code == 404
    assert (await check("x:1", ["a"])).status_code == 404
