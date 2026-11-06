"""Role-play API over lesson scenes."""

from tests.helpers import csrf
from tests.test_learning import child_session, finish, start
from tests.test_scenes import overrides, seed  # noqa: F401  (fixture and seed data)


async def test_roleplay_needs_the_scene_words_introduced(db, client):
    await seed()
    me = await child_session(client)
    assert (await client.get("/api/v1/roleplay?language=de")).json() == []
    s = await start(client, me)
    assert s["scene"]["title"] == "Ahoj"
    # Started is not enough: the words count as met once the lesson is finished.
    assert (await client.get("/api/v1/roleplay?language=de")).json() == []
    await finish(client, me, s)
    scenes = (await client.get("/api/v1/roleplay?language=de")).json()
    # "Pes" has no speakers and its word is still new: only "Ahoj" can be played.
    assert [(x["title"], x["speakers"]) for x in scenes] == [("Ahoj", ["Anna", "Tom"])]
    sid = scenes[0]["id"]

    script = (await client.get(f"/api/v1/roleplay/{sid}?role=Tom")).json()
    lines = script["lines"]
    assert [ln["mine"] for ln in lines] == [False, True, False]
    assert lines[0]["options"] is None
    tom = lines[1]
    assert tom["text"] == "Ich bin Tom. Und du?"
    assert tom["options"][tom["answer"]] == tom["text"] and len(set(tom["options"])) >= 2

    r = await client.post(
        f"/api/v1/roleplay/{sid}/check",
        json={"line": 1, "text": "ich bin Tom und du"},
        headers=csrf(me),
    )
    assert r.status_code == 200
    out = r.json()
    assert [m["verdict"] for m in out["marks"]] == ["case", "ok", "ok", "case", "ok"]

    assert (await client.get(f"/api/v1/roleplay/{sid}?role=Eve")).status_code == 422


async def test_roleplay_unknown_scene_is_404(db, client):
    await seed()
    await child_session(client)
    r = await client.get("/api/v1/roleplay/00000000-0000-0000-0000-000000000000?role=Tom")
    assert r.status_code == 404
