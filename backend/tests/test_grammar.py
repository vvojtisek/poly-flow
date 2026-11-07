"""Grammar lessons and checks end to end through the API, with a controllable clock."""

import uuid
from datetime import timedelta

import pytest
from sqlalchemy import select

from app.api.deps import get_limiter
from app.api.learning import get_now
from app.db.session import get_session
from app.domain.enums import ProgressState
from app.domain.grammar import GrammarPack
from app.main import app
from app.models import GrammarAttempt, GrammarExercise, UserGrammarProgress
from app.services import grammar as svc
from app.services.rate_limit import MemoryAttemptLimiter
from tests.helpers import Clock, csrf, login, make_child, setup_parent


def pack(*, drop_last: bool = False, flagged: bool = True) -> GrammarPack:
    a_ex = [
        {
            "id": "t-a-1",
            "kind": "choice",
            "prompt": "___ Hund",
            "options": ["der", "die", "das"],
            "answers": ["der"],
            "explain": "Hund je mužského rodu.",
        },
        {
            "id": "t-a-2",
            "kind": "gap",
            "prompt": "Ich ___ müde. (sein)",
            "answers": ["bin"],
            "explain": "ich bin",
        },
        {
            "id": "t-a-3",
            "kind": "order",
            "prompt": "Jsem tady.",
            "tokens": ["hier", "bin", "ich"],
            "answers": ["Ich bin hier"],
            "explain": "sloveso druhé",
        },
        {
            "id": "t-a-4",
            "kind": "translate",
            "direction": "cs-target",
            "prompt": "Mám psa.",
            "answers": ["Ich habe einen Hund"],
            "explain": "einen Hund: 4. pád",
        },
    ]
    if flagged:
        a_ex.append(
            {
                "id": "t-a-5",
                "kind": "gap",
                "prompt": "Er ___ ihn. (schlagen)",
                "answers": ["schlägt"],
                "explain": "a -> ä",
                "content_flags": ["violence"],
            }
        )
    if drop_last:
        a_ex = a_ex[:3] + a_ex[4:]  # t-a-4 leaves the pack
    b_ex = [
        {
            "id": f"t-b-{i}",
            "kind": "choice",
            "prompt": "Ich sehe ___ Hund.",
            "options": ["den", "der"],
            "answers": ["den"],
            "explain": "4. pád",
        }
        for i in range(1, 5)
    ]
    unit = {"notes": [{"heading": "H", "text": "T"}], "examples": [{"text": "x", "cs": "y"}]}
    return GrammarPack.model_validate(
        {
            "language": "de",
            "source": "test",
            "license": "MIT",
            "revision": "t1",
            "review_status": "unreviewed",
            "units": [
                {"id": "t-a", "level": "A1", "title": "A", "summary": "a", "exercises": a_ex}
                | unit,
                {"id": "t-b", "level": "A1", "title": "B", "summary": "b", "exercises": b_ex}
                | unit,
            ],
        }
    )


async def seed(p: GrammarPack | None = None) -> None:
    async for db in get_session():
        await svc.upsert_pack(db, p or pack())
        await db.commit()


@pytest.fixture(autouse=True)
def clock():
    c = Clock()
    lim = MemoryAttemptLimiter()
    app.dependency_overrides[get_now] = lambda: c.now
    app.dependency_overrides[get_limiter] = lambda: lim
    yield c
    app.dependency_overrides.clear()


def key() -> str:
    return uuid.uuid4().hex


def right_body(ex: dict) -> dict:
    by_id = {
        "t-a-1": {"choice": 0},
        "t-a-2": {"text": "bin"},
        "t-a-3": {"text": "Ich bin hier"},
        "t-a-4": {"text": "Ich habe einen Hund"},
        "t-a-5": {"text": "schlägt"},
    }
    if ex["unit_id"] == "t-b":
        return {"choice": ex["options"].index("den")}
    return by_id[_exercise_id(ex)]


_ITEM_EXERCISE: dict[str, str] = {}


def _exercise_id(ex: dict) -> str:
    return _ITEM_EXERCISE[ex["item_id"]]


async def remember_items(session_id: str) -> None:
    from app.models import GrammarSessionItem

    async for db in get_session():
        for item in (
            await db.execute(
                select(GrammarSessionItem).where(
                    GrammarSessionItem.session_id == uuid.UUID(session_id)
                )
            )
        ).scalars():
            _ITEM_EXERCISE[str(item.id)] = item.exercise_id


async def adult(client) -> dict:
    return await setup_parent(client)


async def lesson(client, me, unit="t-a") -> dict:
    r = await client.post(f"/api/v1/grammar/units/{unit}/lesson", headers=csrf(me))
    assert r.status_code == 200, r.text
    s = r.json()["session"]
    await remember_items(s["id"])
    return s


async def check(client, me) -> dict | None:
    r = await client.post("/api/v1/grammar/check", json={"language": "de"}, headers=csrf(me))
    assert r.status_code == 200, r.text
    s = r.json()["session"]
    if s:
        await remember_items(s["id"])
    return s


async def nxt(client, sid) -> dict | None:
    r = await client.get(f"/api/v1/grammar/sessions/{sid}/next")
    assert r.status_code == 200, r.text
    return r.json()["item"]


async def answer(client, me, item, body, k=None) -> dict:
    r = await client.post(
        f"/api/v1/grammar/items/{item['item_id']}/answer",
        json={"idempotency_key": k or key(), **body},
        headers=csrf(me),
    )
    assert r.status_code == 200, r.text
    return r.json()


async def complete(client, me, sid) -> dict:
    r = await client.post(f"/api/v1/grammar/sessions/{sid}/complete", headers=csrf(me))
    assert r.status_code == 200, r.text
    return r.json()


async def finish_lesson(client, me, unit="t-a") -> None:
    s = await lesson(client, me, unit)
    while (item := await nxt(client, s["id"])) is not None:
        await answer(client, me, item, right_body(item))
    await complete(client, me, s["id"])


async def progress(unit="t-a") -> UserGrammarProgress | None:
    async for db in get_session():
        return (
            await db.execute(select(UserGrammarProgress).where(UserGrammarProgress.unit_id == unit))
        ).scalar_one_or_none()


async def test_tree_lists_units_in_order_with_a_recommendation(db, client):
    await seed()
    me = await adult(client)
    r = await client.get("/api/v1/grammar?language=de")
    assert r.status_code == 200, r.text
    t = r.json()
    assert t["open"] is True and t["recommended"] == "t-a" and t["due"] == 0
    assert t["review_status"] == "unreviewed"
    assert [u["id"] for u in t["levels"][0]["units"]] == ["t-a", "t-b"]
    assert {u["status"] for u in t["levels"][0]["units"]} == {"new"}
    assert all(u["objective"] == u["summary"] for u in t["levels"][0]["units"])
    assert me


async def test_search_index_has_plain_explanation_text(db, client):
    await seed()
    await adult(client)
    r = await client.get("/api/v1/grammar/search-index?language=de")
    assert r.status_code == 200, r.text
    rows = r.json()
    assert [x["id"] for x in rows] == ["t-a", "t-b"]
    assert all("H" in x["text"] and "T" in x["text"] and "x" in x["text"] for x in rows)
    assert all("**" not in x["text"] for x in rows)


async def test_exercise_never_leaks_answers(db, client):
    await seed()
    me = await adult(client)
    s = await lesson(client, me)
    assert s["unit"]["notes"][0]["heading"] == "H"
    item = await nxt(client, s["id"])
    assert "answers" not in item and "explain" not in item
    assert item["kind"] == "choice" and item["options"] == ["der", "die", "das"]


async def test_lesson_wrong_answer_explains_and_retries_without_evidence(db, client):
    await seed()
    me = await adult(client)
    s = await lesson(client, me)
    item = await nxt(client, s["id"])
    r = await answer(client, me, item, {"choice": 1})
    assert r["correct"] is False and r["can_retry"] is True and r["counted"] is False
    assert r["expected"] == "der" and r["explanation"] == "Hund je mužského rodu."
    assert r["error"] == "article"
    r = await answer(client, me, item, {"choice": 0})
    assert r["correct"] is True and r["task_done"] is True and r["counted"] is False
    assert await progress() is None  # practice is never evidence


async def test_finished_lesson_makes_unit_checkable_from_tomorrow(db, client, clock):
    await seed()
    me = await adult(client)
    await finish_lesson(client, me)
    p = await progress()
    assert p.studied_at is not None and p.state == ProgressState.LEARNING
    assert await check(client, me) is None  # not today
    t = (await client.get("/api/v1/grammar?language=de")).json()
    assert t["levels"][0]["units"][0]["status"] == "studied"
    assert t["recommended"] == "t-b"
    clock.advance(days=1)
    s = await check(client, me)
    assert s is not None and s["mode"] == "check" and s["total"] == 2


async def test_check_is_one_attempt_and_moves_the_schedule(db, client, clock):
    await seed()
    me = await adult(client)
    await finish_lesson(client, me)
    clock.advance(days=1)
    s = await check(client, me)
    first = await nxt(client, s["id"])
    r = await answer(
        client, me, first, {"text": "falsch"} if first["kind"] != "choice" else {"choice": 2}
    )
    assert r["correct"] is False and r["task_done"] is True and r["can_retry"] is False
    assert r["explanation"]  # the rule is explained once the item is closed
    r2 = await client.post(
        f"/api/v1/grammar/items/{first['item_id']}/answer",
        json={"idempotency_key": key(), **right_body(first)},
        headers=csrf(me),
    )
    assert r2.status_code == 409  # no second attempt in a check
    second = await nxt(client, s["id"])
    r = await answer(client, me, second, right_body(second))
    assert r["correct"] is True and r["counted"] is True
    p = await progress()
    assert p.error_count == 1 and p.correct_count == 1
    assert p.next_review_at > clock.now
    tree = (await client.get("/api/v1/grammar?language=de")).json()
    unit = next(u for lv in tree["levels"] for u in lv["units"] if u["id"] == "t-a")
    assert unit["checked_correct"] == 1 and unit["checked_errors"] == 1


async def test_duplicate_submission_replays(db, client, clock):
    await seed()
    me = await adult(client)
    s = await lesson(client, me)
    item = await nxt(client, s["id"])
    k = key()
    a = await answer(client, me, item, {"choice": 1}, k)
    b = await answer(client, me, item, {"choice": 1}, k)
    assert a == b
    async for db_ in get_session():
        n = len(list((await db_.execute(select(GrammarAttempt))).scalars()))
    assert n == 1


async def test_missed_check_exercise_comes_back_in_the_next_lesson_and_check(db, client, clock):
    await seed()
    me = await adult(client)
    await finish_lesson(client, me)
    clock.advance(days=1)
    s = await check(client, me)
    missed = None
    while (item := await nxt(client, s["id"])) is not None:
        if missed is None:
            await answer(
                client, me, item, {"text": "x"} if item["kind"] != "choice" else {"choice": 2}
            )
            missed = _exercise_id(item)
        else:
            await answer(client, me, item, right_body(item))
    await complete(client, me, s["id"])
    # Another unit's lesson brings the missed exercise back as remediation.
    s = await lesson(client, me, "t-b")
    assert s["summary"] == {}
    items = []
    while (item := await nxt(client, s["id"])) is not None:
        items.append(item)
        await answer(client, me, item, right_body(item))
    remediation = [i for i in items if i["is_remediation"]]
    assert [_exercise_id(i) for i in remediation] == [missed]
    done = await complete(client, me, s["id"])
    assert done["summary"]["remediation"] == 1
    # The next check asks the missed exercise again, flagged as targeted.
    clock.advance(days=1)
    s = await check(client, me)
    asked = []
    while (item := await nxt(client, s["id"])) is not None:
        asked.append((_exercise_id(item), item["is_remediation"]))
        await answer(client, me, item, right_body(item))
    assert (missed, True) in asked


async def test_child_never_gets_flagged_exercises(db, client):
    await seed()
    parent = await setup_parent(client)
    await make_child(client, parent)
    me = await login(client, "eva", "4321")
    s = await lesson(client, me)
    ids = set()
    while (item := await nxt(client, s["id"])) is not None:
        ids.add(_exercise_id(item))
        await answer(client, me, item, right_body(item))
    assert "t-a-5" not in ids and len(ids) == 4
    t = (await client.get("/api/v1/grammar?language=de")).json()
    assert t["levels"][0]["units"][0]["exercises"] == 4


async def test_known_after_three_checks_on_two_days_then_mastered(db, client, clock):
    await seed(pack(flagged=False))
    me = await adult(client)
    await finish_lesson(client, me)
    for _ in range(5):
        p = await progress()
        if p.known_since_at is not None:
            break
        clock.now = max(clock.now, p.next_review_at) + timedelta(minutes=1)
        s = await check(client, me)
        while (item := await nxt(client, s["id"])) is not None:
            await answer(client, me, item, right_body(item))
        await complete(client, me, s["id"])
    p = await progress()
    # Known: three first-try check answers on two days. Mastery waits a week after that.
    assert p.known_since_at is not None and p.state == ProgressState.LEARNING
    clock.now = max(clock.now + timedelta(days=7), p.next_review_at) + timedelta(minutes=1)
    s = await check(client, me)
    while (item := await nxt(client, s["id"])) is not None:
        await answer(client, me, item, right_body(item))
    assert (await progress()).state == ProgressState.MASTERED
    t = (await client.get("/api/v1/grammar?language=de")).json()
    assert t["levels"][0]["units"][0]["status"] == "mastered"


async def test_decay_sweep_is_idempotent(db, client, clock):
    await seed()
    me = await adult(client)
    await finish_lesson(client, me)
    clock.advance(days=1)
    s = await check(client, me)
    while (item := await nxt(client, s["id"])) is not None:
        await answer(client, me, item, right_body(item))
    later = clock.now + timedelta(days=45)
    async for db_ in get_session():
        assert await svc.decay_sweep(db_, later) == 1
        assert await svc.decay_sweep(db_, later + timedelta(days=1)) == 0
        await db_.commit()
    p = await progress()
    assert p.next_review_at <= later and p.review_streak == 0


async def test_reimport_retires_removed_exercises_and_keeps_progress(db, client, clock):
    await seed()
    me = await adult(client)
    await finish_lesson(client, me)
    await seed(pack(drop_last=True))
    async for db_ in get_session():
        active = {e.id: e.active for e in (await db_.execute(select(GrammarExercise))).scalars()}
    assert active["t-a-4"] is False and active["t-a-1"] is True
    assert (await progress()).studied_at is not None


async def test_starting_another_unit_sets_the_open_lesson_aside(db, client):
    await seed()
    me = await adult(client)
    a = await lesson(client, me, "t-a")
    again = await lesson(client, me, "t-a")
    assert again["id"] == a["id"]
    b = await lesson(client, me, "t-b")
    assert b["id"] != a["id"]
    old = (await client.get(f"/api/v1/grammar/sessions/{a['id']}")).json()
    assert old["status"] == "completed" and old["summary"]["abandoned"] is True
    assert (await progress()) is None  # an abandoned lesson does not count as studied


async def test_other_profiles_cannot_answer_my_items(db, client):
    await seed()
    parent = await setup_parent(client)
    await make_child(client, parent)
    s = await lesson(client, parent)
    item = await nxt(client, s["id"])
    me = await login(client, "eva", "4321")
    r = await client.post(
        f"/api/v1/grammar/items/{item['item_id']}/answer",
        json={"idempotency_key": key(), "choice": 0},
        headers=csrf(me),
    )
    assert r.status_code == 404
    assert (await client.get(f"/api/v1/grammar/sessions/{s['id']}")).status_code == 404
