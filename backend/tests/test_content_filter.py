"""Child profiles: age-appropriate content filter on lexicon items; admin content edits."""

import pytest
from sqlalchemy import select, update

from app.api.deps import get_limiter
from app.api.learning import get_now
from app.cli import LexiconRow, RowError, read_rows, upsert_lexicon
from app.db.session import get_session
from app.domain.enums import ContentFlag
from app.main import app
from app.models import LearningTask, LexiconItem, UserWordProgress
from app.services.rate_limit import MemoryAttemptLimiter
from tests.helpers import Clock, csrf, login, make_child, setup_parent

WORDS = [
    ("Haus", "NOUN", "dům", ""),
    ("Krieg", "NOUN", "válka", "violence"),
    ("Baum", "NOUN", "strom", ""),
    ("Mist", "NOUN", "sakra", "profanity"),
    ("gehen", "VERB", "jít", ""),
    ("Hund", "NOUN", "pes", ""),
]
FLAGGED = {"Krieg", "Mist"}


@pytest.fixture(autouse=True)
def overrides():
    clock = Clock()
    lim = MemoryAttemptLimiter()
    app.dependency_overrides[get_now] = lambda: clock.now
    app.dependency_overrides[get_limiter] = lambda: lim
    yield
    app.dependency_overrides.clear()


async def seed(flags: bool = True) -> None:
    await upsert_lexicon(
        [
            LexiconRow(
                language="de",
                rank=i + 1,
                lemma=w,
                pos=pos,
                translation_cs=cs,
                content_flags=f if flags else "",
            )
            for i, (w, pos, cs, f) in enumerate(WORDS)
        ]
    )


async def lesson_content(client, me, mode: str = "learn") -> tuple[set[str], set[str]]:
    """(lemmas taught, every Czech gloss shown as a recognition option) for a new session."""
    r = await client.post(
        "/api/v1/learning/sessions", json={"language": "de", "mode": mode}, headers=csrf(me)
    )
    assert r.status_code == 200, r.text
    sid = r.json()["session"]["id"]
    async for db in get_session():
        tasks = (
            (await db.execute(select(LearningTask).where(LearningTask.session_id == sid)))
            .scalars()
            .all()
        )
        lemmas = set()
        for t in tasks:
            lemmas.add((await db.get(LexiconItem, t.lexicon_item_id)).lemma)
        options = {o for t in tasks for o in t.payload.get("options", [])}
    return lemmas, options


async def test_child_never_gets_flagged_items(db, client):
    await seed()
    parent = await setup_parent(client)
    await make_child(client, parent)
    child = await login(client, "eva", "4321")
    lemmas, options = await lesson_content(client, child)
    assert lemmas and not lemmas & FLAGGED
    assert options and not options & {"válka", "sakra"}


async def test_adult_gets_flagged_items_but_profanity_only_by_choice(db, client):
    await seed()
    parent = await setup_parent(client)
    lemmas, options = await lesson_content(client, parent)
    assert "Krieg" in lemmas and "Mist" not in lemmas and "sakra" not in options


async def test_adult_opts_into_profanity(db, client):
    await seed()
    parent = await setup_parent(client)
    r = await client.patch(
        "/api/v1/me/profile", json={"settings": {"learn_profanity": True}}, headers=csrf(parent)
    )
    assert r.status_code == 200 and r.json()["settings"]["learn_profanity"] is True
    lemmas, _ = await lesson_content(client, parent)
    assert FLAGGED <= lemmas


async def test_child_cannot_opt_into_profanity(db, client):
    await seed()
    parent = await setup_parent(client)
    await make_child(client, parent)
    child = await login(client, "eva", "4321")
    r = await client.patch(
        "/api/v1/me/profile", json={"settings": {"learn_profanity": True}}, headers=csrf(child)
    )
    assert r.status_code == 422 and r.json()["detail"] == "profanity_adults_only"
    r = await client.patch(
        "/api/v1/me/profile", json={"settings": {"learn_profanity": False}}, headers=csrf(child)
    )
    assert r.status_code == 200


async def test_item_flagged_later_leaves_child_reviews(db, client):
    await seed(flags=False)
    parent = await setup_parent(client)
    await make_child(client, parent)
    child = await login(client, "eva", "4321")
    lemmas, _ = await lesson_content(client, child)
    assert "Krieg" in lemmas
    # Finish the lesson (introduces its words), make them checkable now, then flag one word.
    sid = (await client.get("/api/v1/learning/sessions/current?language=de")).json()["session"][
        "id"
    ]
    r = await client.post(f"/api/v1/learning/sessions/{sid}/complete", headers=csrf(child))
    assert r.status_code == 200
    async for s in get_session():
        await s.execute(update(UserWordProgress).values(next_review_at=Clock().now))
        await s.execute(
            update(LexiconItem)
            .where(LexiconItem.lemma == "Krieg")
            .values(content_flags=["violence"])
        )
        await s.commit()
    lemmas, _ = await lesson_content(client, child, "check")
    assert lemmas and "Krieg" not in lemmas


async def test_reimport_only_adds_flags(db):
    await seed()
    await seed(flags=False)  # a file without the column must not unflag anything
    async for s in get_session():
        flags = dict((await s.execute(select(LexiconItem.lemma, LexiconItem.content_flags))).all())
    assert flags["Krieg"] == ["violence"] and flags["Mist"] == ["profanity"]
    assert flags["Haus"] == []


async def test_admin_edits_content_learners_cannot(db, client):
    await seed()
    parent = await setup_parent(client)
    r = await client.get("/api/v1/lexicon", params={"language": "de", "flagged": True})
    assert r.status_code == 200
    assert {i["lemma"] for i in r.json()} == FLAGGED
    baum = next(
        i
        for i in (await client.get("/api/v1/lexicon", params={"language": "de"})).json()
        if i["lemma"] == "Baum"
    )
    r = await client.patch(
        f"/api/v1/lexicon/{baum['id']}",
        json={"content_flags": ["violence", "violence"], "ipa": "baʊ̯m", "example_sentence": ""},
        headers=csrf(parent),
    )
    assert r.status_code == 200, r.text
    assert r.json()["content_flags"] == ["violence"] and r.json()["ipa"] == "baʊ̯m"
    assert r.json()["example_sentence"] is None
    r = await client.patch(
        f"/api/v1/lexicon/{baum['id']}", json={"content_flags": ["gore"]}, headers=csrf(parent)
    )
    assert r.status_code == 422
    r = await client.patch(
        f"/api/v1/lexicon/{baum['id']}", json={"translation_cs": None}, headers=csrf(parent)
    )
    assert r.status_code == 422

    await make_child(client, parent)
    child = await login(client, "eva", "4321")
    assert (await client.get("/api/v1/lexicon", params={"language": "de"})).status_code == 403
    r = await client.patch(
        f"/api/v1/lexicon/{baum['id']}", json={"content_flags": []}, headers=csrf(child)
    )
    assert r.status_code == 403


def test_csv_content_flags(tmp_path):
    p = tmp_path / "x.csv"
    p.write_text(
        "language,rank,lemma,pos,translation_cs,content_flags\n"
        "de,1,Krieg,NOUN,válka,violence | profanity\n"
        "de,2,Haus,NOUN,dům,\n"
    )
    rows = read_rows(p, LexiconRow)
    assert rows[0].to_db()["content_flags"] == ["profanity", "violence"]
    assert rows[1].to_db()["content_flags"] == []
    assert ContentFlag.VIOLENCE in rows[0].content_flags
    p.write_text(
        "language,rank,lemma,pos,translation_cs,content_flags\nde,1,Krieg,NOUN,válka,gore\n"
    )
    with pytest.raises(RowError):
        read_rows(p, LexiconRow)
