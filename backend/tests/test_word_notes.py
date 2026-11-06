"""Memory hooks: a learner's own note per word, shown on word cards, in the dictionary and after
a miss."""

import uuid

from sqlalchemy import select

from app.db.session import get_session
from app.models import LearningTask, LexiconItem
from tests.helpers import csrf
from tests.test_learning import child_session, key, next_task, start
from tests.test_scenes import overrides, seed  # noqa: F401  (fixture and seed data)


async def item_id(lemma: str) -> uuid.UUID:
    async for s in get_session():
        return (
            await s.execute(select(LexiconItem.id).where(LexiconItem.lemma == lemma))
        ).scalar_one()


async def test_note_lifecycle_and_lesson_card(db, client):
    await seed()
    me = await child_session(client)
    ich = await item_id("ich")
    r = await client.put(
        f"/api/v1/words/{ich}/note",
        json={"text": "  ich   = já,  jako  'ich bin'  "},
        headers=csrf(me),
    )
    assert r.status_code == 200 and r.json()["note"] == "ich = já, jako 'ich bin'"
    s = await start(client, me)
    cards = {c["lemma"]: c for c in s["words"]}
    assert cards["ich"]["note"] == "ich = já, jako 'ich bin'"
    assert cards["heißen"]["note"] is None
    # Too long is trimmed, empty removes it.
    r = await client.put(f"/api/v1/words/{ich}/note", json={"text": "x" * 500}, headers=csrf(me))
    assert len(r.json()["note"]) == 280
    r = await client.put(f"/api/v1/words/{ich}/note", json={"text": "  "}, headers=csrf(me))
    assert r.json()["note"] is None
    missing = uuid.uuid4()
    r = await client.put(f"/api/v1/words/{missing}/note", json={"text": "x"}, headers=csrf(me))
    assert r.status_code == 404


async def test_hook_is_returned_after_a_miss(db, client):
    await seed()
    me = await child_session(client)
    s = await start(client, me)
    task = await next_task(client, s["id"])
    async for db_s in get_session():
        item = (
            await db_s.execute(
                select(LearningTask.lexicon_item_id).where(LearningTask.id == uuid.UUID(task["id"]))
            )
        ).scalar_one()
    await client.put(f"/api/v1/words/{item}/note", json={"text": "můj háček"}, headers=csrf(me))
    r = await client.post(
        f"/api/v1/learning/tasks/{task['id']}/reveal",
        json={"idempotency_key": key()},
        headers=csrf(me),
    )
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["correct"] is False and out["hook"] == "můj háček"
