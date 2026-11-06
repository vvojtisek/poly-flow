"""Review of a finished check: every word, the first answer, and where it stands now."""

from tests.helpers import csrf, seed_words
from tests.test_learning import (  # noqa: F401  (fixtures)
    answer,
    child_session,
    clock,
    finish,
    next_task,
    overrides,
    run_lesson,
    start,
    wrong_answer,
)


async def test_check_review(db, client, clock):  # noqa: F811  (clock is a fixture)
    await seed_words()
    me = await child_session(client)
    await run_lesson(client, me)
    clock.advance(days=1)
    s = await start(client, me, "de", "check")
    # An unfinished session has no review yet.
    r = await client.get(f"/api/v1/learning/sessions/{s['id']}/review")
    assert r.status_code == 409
    first = await next_task(client, s["id"])
    body = await wrong_answer(first)
    assert (await answer(client, me, first, body)).status_code == 200
    await finish(client, me, s)
    out = (await client.get(f"/api/v1/learning/sessions/{s['id']}/review")).json()
    assert out["mode"] == "check"
    items = out["items"]
    assert items[0]["first_try"] is False and items[0]["answered"] is not None
    assert all(i["first_try"] is None for i in items[1:])  # left unanswered
    assert {"lemma", "expected", "passive_known", "next_review_at", "note"} <= set(items[0])
    # Another profile cannot read it.
    other = await client.post("/api/v1/auth/logout", headers=csrf(me))
    assert other.status_code in (200, 204)
    assert (await client.get(f"/api/v1/learning/sessions/{s['id']}/review")).status_code == 401
