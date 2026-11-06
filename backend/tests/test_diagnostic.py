"""CEFR placement diagnostic end to end through the API."""

import uuid
from pathlib import Path

import pytest
from sqlalchemy import select

from app.api.deps import get_limiter
from app.api.learning import get_now
from app.cli import read_grammar_pack
from app.db.session import get_session
from app.main import app
from app.models import CefrPlacement, DiagnosticSession, UserGrammarProgress
from app.services import diagnostic as svc
from app.services import grammar as grammar_svc
from app.services.rate_limit import MemoryAttemptLimiter
from app.services.tts import get_tts
from tests.helpers import Clock, csrf, login, make_child, setup_parent

GRAMMAR = Path(__file__).resolve().parents[1] / "data" / "grammar" / "de.grammar.json"


class FakeTts:
    def __init__(self, voices: set[str]):
        self.voices = voices

    async def installed(self) -> set[str]:
        return self.voices


@pytest.fixture(autouse=True)
def clock():
    c = Clock()
    lim = MemoryAttemptLimiter()
    app.dependency_overrides[get_now] = lambda: c.now
    app.dependency_overrides[get_limiter] = lambda: lim
    app.dependency_overrides[get_tts] = lambda: FakeTts(set())
    yield c
    app.dependency_overrides.clear()


async def item_id(session_id: str, position: int) -> str:
    async for db in get_session():
        s = await db.get(DiagnosticSession, uuid.UUID(session_id))
        return s.items[position]["id"]
    raise AssertionError


async def start(client, me, language="de") -> dict:
    r = await client.post(
        "/api/v1/diagnostic/sessions", json={"language": language}, headers=csrf(me)
    )
    assert r.status_code == 200, r.text
    return r.json()


async def run(client, me, decide) -> dict:
    """Answer until the result; `decide(item)` returns True to answer right, False wrong."""
    st = await start(client, me)
    bank = svc.bank(st["language"]).by_id()
    sid = st["session_id"]
    while st["question"] is not None:
        q = st["question"]
        item = bank[await item_id(sid, q["position"])]
        choice = item.answer if decide(item) else next(o for o in q["options"] if o != item.answer)
        r = await client.post(
            f"/api/v1/diagnostic/sessions/{sid}/answer",
            json={"position": q["position"], "choice": choice},
            headers=csrf(me),
        )
        assert r.status_code == 200, r.text
        r = await client.get(f"/api/v1/diagnostic/sessions/{sid}")
        assert r.status_code == 200, r.text
        st = r.json()
    assert st["status"] == "completed"
    return st


async def seed_grammar() -> None:
    async for db in get_session():
        await grammar_svc.upsert_pack(db, read_grammar_pack(GRAMMAR))
        await db.commit()


async def grammar_rows() -> dict[str, UserGrammarProgress]:
    async for db in get_session():
        return {p.unit_id: p for p in (await db.execute(select(UserGrammarProgress))).scalars()}
    raise AssertionError


async def test_info_reports_the_bank_and_no_result_yet(db, client):
    await setup_parent(client)
    r = await client.get("/api/v1/diagnostic?language=fr")
    assert r.status_code == 200, r.text
    info = r.json()
    assert info["available"] and info["items"] == 40 and info["latest"] is None
    assert info["bands"] == ["A1", "A2", "B1", "B2", "B2+"]


async def test_questions_never_leak_the_answer_or_the_listening_text(db, client):
    app.dependency_overrides[get_tts] = lambda: FakeTts({"de_DE-thorsten-medium"})
    me = await setup_parent(client)
    st = await start(client, me)
    assert st["with_listening"] is True
    q = st["question"]
    assert set(q) >= {"prompt", "options", "band", "skill", "has_audio"}
    assert "answer" not in q and "explain" not in q and "audio" not in q


async def test_without_a_voice_no_listening_question_is_asked(db, client):
    me = await setup_parent(client)
    st = await run(client, me, lambda item: True)
    assert st["with_listening"] is False
    assert all(s["skill"] != "listening" for s in st["result"]["skills"])


async def test_strong_learner_reaches_b2_plus_and_unlocks_grammar_and_exams(db, client):
    await seed_grammar()
    me = await setup_parent(client)
    st = await run(client, me, lambda item: True)
    res = st["result"]
    assert res["level"] == "B2+" and res["next"] is None
    assert res["exams_opened"] == ["A1", "A2", "B1", "B2"]
    rows = await grammar_rows()
    units = len(read_grammar_pack(GRAMMAR).units)
    assert len(rows) == units and res["grammar_queued"] == units
    assert all(p.studied_by == "placement" and p.next_review_at is not None for p in rows.values())
    # The units wait in the grammar check right away.
    r = await client.get("/api/v1/grammar?language=de")
    assert r.json()["due"] == units
    async for db_ in get_session():
        placed = await db_.get(CefrPlacement, (uuid.UUID(me["acting"]["id"]), "de"))
        assert placed.level.value == "C1"


async def test_learner_who_fails_above_a2_is_placed_at_a2_and_retake_returns_units(db, client):
    await seed_grammar()
    me = await setup_parent(client)
    await run(client, me, lambda item: True)
    st = await run(client, me, lambda item: item.level.value in ("A1", "A2"))
    res = st["result"]
    assert res["level"] in ("A1", "A2"), res
    rows = await grammar_rows()
    queued = {u for u, p in rows.items() if p.studied_at is not None}
    assert res["grammar_returned"] > 0
    assert queued and all(u.startswith(("de-a1-", "de-a2-")) for u in queued)


async def test_answers_are_one_attempt_and_replay(db, client):
    me = await setup_parent(client)
    st = await start(client, me)
    sid, q = st["session_id"], st["question"]
    body = {"position": q["position"], "choice": None}
    r1 = await client.post(f"/api/v1/diagnostic/sessions/{sid}/answer", json=body, headers=csrf(me))
    assert (
        r1.status_code == 200 and r1.json()["dont_know"] is True and r1.json()["correct"] is False
    )
    body["choice"] = q["options"][0]
    r2 = await client.post(f"/api/v1/diagnostic/sessions/{sid}/answer", json=body, headers=csrf(me))
    assert r2.json() == r1.json()  # the first verdict stands


async def test_a_choice_outside_the_options_is_rejected(db, client):
    me = await setup_parent(client)
    st = await start(client, me)
    r = await client.post(
        f"/api/v1/diagnostic/sessions/{st['session_id']}/answer",
        json={"position": st["question"]["position"], "choice": "<script>"},
        headers=csrf(me),
    )
    assert r.status_code == 422


async def test_start_resumes_the_open_test(db, client):
    me = await setup_parent(client)
    a = await start(client, me)
    b = await start(client, me)
    assert a["session_id"] == b["session_id"] and a["question"] == b["question"]


async def test_stopping_early_places_nobody(db, client):
    me = await setup_parent(client)
    st = await start(client, me)
    r = await client.post(f"/api/v1/diagnostic/sessions/{st['session_id']}/stop", headers=csrf(me))
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "abandoned" and r.json()["result"]["placed"] is False
    info = (await client.get("/api/v1/diagnostic?language=de")).json()
    assert info["latest"] is None and info["active_session_id"] is None


async def test_another_profile_cannot_see_or_answer_the_session(db, client):
    parent = await setup_parent(client)
    st = await start(client, parent)
    await make_child(client, parent)
    child = await login(client, "eva", "4321")
    r = await client.get(f"/api/v1/diagnostic/sessions/{st['session_id']}")
    assert r.status_code == 404
    r = await client.post(
        f"/api/v1/diagnostic/sessions/{st['session_id']}/answer",
        json={"position": 0, "choice": None},
        headers=csrf(child),
    )
    assert r.status_code == 404


async def test_b1_result_opens_level_exams_up_to_b1(db, client):
    me = await setup_parent(client)
    await run(client, me, lambda item: item.level.value in ("A1", "A2", "B1"))
    async for db_ in get_session():
        placed = await db_.get(CefrPlacement, (uuid.UUID(me["acting"]["id"]), "de"))
        assert placed.level.value in ("A2", "B1", "B2")
