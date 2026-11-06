"""My dictionary: own words only, status filters, search, detail and the content filter."""

import uuid

import pytest
from sqlalchemy import select

from app.api.deps import get_limiter
from app.api.learning import get_now
from app.cli import LexiconRow, upsert_lexicon
from app.db.session import get_session
from app.domain.enums import ProgressState
from app.main import app
from app.models import LexiconItem, UserWordProgress
from app.services.rate_limit import MemoryAttemptLimiter
from tests.helpers import Clock, login, make_child, setup_parent


@pytest.fixture(autouse=True)
def clock():
    c = Clock()
    app.dependency_overrides[get_now] = lambda: c.now
    app.dependency_overrides[get_limiter] = lambda: MemoryAttemptLimiter()
    yield c
    app.dependency_overrides.clear()


async def seed(uid: uuid.UUID, clock) -> dict[str, uuid.UUID]:
    await upsert_lexicon(
        [
            LexiconRow(
                language="de", rank=1, lemma="Haus", pos="NOUN", translation_cs="dům", gender="das"
            ),
            LexiconRow(language="de", rank=2, lemma="gehen", pos="VERB", translation_cs="jít"),
            LexiconRow(language="de", rank=3, lemma="schön", pos="ADJ", translation_cs="hezký"),
            LexiconRow(
                language="de",
                rank=4,
                lemma="Mord",
                pos="NOUN",
                translation_cs="vražda",
                content_flags=["violence"],
            ),
            LexiconRow(language="de", rank=5, lemma="neu", pos="ADJ", translation_cs="nový"),
        ]
    )
    async for db in get_session():
        ids = {i.lemma: i.id for i in (await db.execute(select(LexiconItem))).scalars()}
        db.add_all(
            [
                UserWordProgress(
                    user_id=uid,
                    lexicon_item_id=ids["Haus"],
                    introduced_at=clock.now,
                    passive_known=True,
                    active_known=True,
                    state=ProgressState.MASTERED,
                    next_review_at=clock.now,
                    policy_version="v4",
                ),
                UserWordProgress(
                    user_id=uid,
                    lexicon_item_id=ids["gehen"],
                    introduced_at=clock.now,
                    passive_known=True,
                    policy_version="v4",
                ),
                UserWordProgress(
                    user_id=uid,
                    lexicon_item_id=ids["schön"],
                    introduced_at=clock.now,
                    policy_version="v4",
                ),
                UserWordProgress(
                    user_id=uid,
                    lexicon_item_id=ids["Mord"],
                    introduced_at=clock.now,
                    policy_version="v4",
                ),
            ]
        )
        await db.commit()
        return ids
    raise AssertionError


async def test_lists_only_own_words_with_status_and_search(db, client, clock):
    me = await setup_parent(client)
    ids = await seed(uuid.UUID(me["acting"]["id"]), clock)
    out = (await client.get("/api/v1/words?language=de")).json()
    assert [w["lemma"] for w in out["items"]] == ["Haus", "gehen", "schön", "Mord"]  # never "neu"
    assert out["counts"] == {"mastered": 1, "known": 0, "passive": 1, "learning": 2, "seen": 0}
    assert (await client.get("/api/v1/words?language=de&q=JÍ")).json()["items"][0][
        "lemma"
    ] == "gehen"
    assert (await client.get("/api/v1/words?language=de&q=%25")).json()["total"] == 0
    assert (await client.get("/api/v1/words?language=de&status=passive")).json()["total"] == 1
    assert [
        w["lemma"] for w in (await client.get("/api/v1/words?language=de&due=true")).json()["items"]
    ] == ["Haus"]
    detail = (await client.get(f"/api/v1/words/{ids['Haus']}")).json()
    assert detail["gender"] == "das" and detail["status"] == "mastered" and detail["history"] == []
    assert (await client.get(f"/api/v1/words/{ids['neu']}")).status_code == 404


async def test_child_never_sees_flagged_words_and_cannot_read_parents(db, client, clock):
    parent = await setup_parent(client)
    child_profile = await make_child(client, parent)
    ids = await seed(uuid.UUID(child_profile["id"]), clock)
    await login(client, "eva", "4321")
    out = (await client.get("/api/v1/words?language=de")).json()
    assert "Mord" not in [w["lemma"] for w in out["items"]]
    assert (await client.get(f"/api/v1/words/{ids['Mord']}")).status_code == 404
