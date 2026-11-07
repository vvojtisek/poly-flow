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
from app.models import LexiconItem, Scene, SceneWord, UserWordProgress
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


async def seed_scenes() -> dict[str, uuid.UUID]:
    async for db in get_session():
        ids = {i.lemma: i.id for i in (await db.execute(select(LexiconItem))).scalars()}
        home = Scene(
            language="de",
            slug="home",
            position=1,
            title_cs="Doma",
            lines=[
                {"speaker": "A", "text": "Ein Haustier? Wir gehen.", "cs": "Mazlíček? Jdeme."},
                {"speaker": "B", "text": "Das Haus ist neu.", "cs": "Ten dům je nový."},
            ],
        )
        crime = Scene(language="de", slug="crime", position=2, title_cs="Detektivka")
        db.add_all([home, crime])
        await db.flush()
        db.add_all(
            [
                SceneWord(scene_id=home.id, lexicon_item_id=ids["Haus"], position=1),
                SceneWord(scene_id=home.id, lexicon_item_id=ids["neu"], position=2),
                SceneWord(scene_id=crime.id, lexicon_item_id=ids["Mord"], position=1),
            ]
        )
        await db.commit()
        return {"home": home.id, "crime": crime.id}
    raise AssertionError


async def test_groups_count_levels_and_topics_from_own_words(db, client, clock):
    me = await setup_parent(client)
    await seed(uuid.UUID(me["acting"]["id"]), clock)
    scenes = await seed_scenes()
    out = (await client.get("/api/v1/words/groups?language=de")).json()
    assert out["levels"] == [
        {"key": "A1", "first_rank": 1, "last_rank": 500, "total": 5, "mine": 4}
    ]
    assert out["topics"] == [
        {"id": str(scenes["home"]), "title": "Doma", "total": 2, "mine": 1},
        {"id": str(scenes["crime"]), "title": "Detektivka", "total": 1, "mine": 1},
    ]


async def test_deck_is_scoped_own_words_due_first(db, client, clock):
    me = await setup_parent(client)
    await seed(uuid.UUID(me["acting"]["id"]), clock)
    scenes = await seed_scenes()
    level = (await client.get("/api/v1/words/deck?language=de&level=A1")).json()
    # Haus is due (first); "neu" was never met, so it is never a card.
    assert [c["lemma"] for c in level["items"]] == ["Haus", "gehen", "schön", "Mord"]
    assert level["total"] == 4 and level["items"][0]["due"] is True
    topic = (await client.get(f"/api/v1/words/deck?language=de&topic={scenes['home']}")).json()
    assert [c["lemma"] for c in topic["items"]] == ["Haus"]
    assert (await client.get("/api/v1/words/deck?language=de&level=B1")).json()["items"] == []
    assert (await client.get("/api/v1/words/deck?language=de")).status_code == 422
    both = f"/api/v1/words/deck?language=de&level=A1&topic={scenes['home']}"
    assert (await client.get(both)).status_code == 422
    assert (await client.get("/api/v1/words/deck?language=de&level=Z9")).status_code == 422
    other = f"/api/v1/words/deck?language=fr&topic={scenes['home']}"
    assert (await client.get(other)).status_code == 404


async def test_child_groups_and_decks_hide_flagged_words_and_scenes(db, client, clock):
    parent = await setup_parent(client)
    child_profile = await make_child(client, parent)
    await seed(uuid.UUID(child_profile["id"]), clock)
    scenes = await seed_scenes()
    await login(client, "eva", "4321")
    out = (await client.get("/api/v1/words/groups?language=de")).json()
    assert out["levels"][0]["total"] == 4 and out["levels"][0]["mine"] == 3
    assert [t["title"] for t in out["topics"]] == ["Doma"]
    deck = (await client.get("/api/v1/words/deck?language=de&level=A1")).json()
    assert "Mord" not in [c["lemma"] for c in deck["items"]]
    crime = f"/api/v1/words/deck?language=de&topic={scenes['crime']}"
    assert (await client.get(crime)).status_code == 404


async def test_word_list_filters_by_level_and_topic(db, client, clock):
    me = await setup_parent(client)
    await seed(uuid.UUID(me["acting"]["id"]), clock)
    scenes = await seed_scenes()
    home = (await client.get(f"/api/v1/words?language=de&topic={scenes['home']}")).json()
    assert [w["lemma"] for w in home["items"]] == ["Haus"]
    assert home["counts"]["mastered"] == 1 and home["counts"]["learning"] == 0
    assert (await client.get("/api/v1/words?language=de&level=A1")).json()["total"] == 4
    assert (await client.get("/api/v1/words?language=de&level=B2")).json()["total"] == 0
    assert (await client.get("/api/v1/words?language=de&level=nope")).status_code == 422


async def test_word_detail_shows_the_lesson_scenes_that_teach_it(db, client, clock):
    parent = await setup_parent(client)
    child_profile = await make_child(client, parent)
    ids = await seed(uuid.UUID(parent["acting"]["id"]), clock)
    await seed(uuid.UUID(child_profile["id"]), clock)
    scenes = await seed_scenes()
    async for db_ in get_session():
        # Haus also appears in the crime scene, which a child profile never gets as a whole.
        db_.add(SceneWord(scene_id=scenes["crime"], lexicon_item_id=ids["Haus"], position=2))
        await db_.commit()
        break
    out = (await client.get(f"/api/v1/words/{ids['Haus']}")).json()
    assert out["contexts"] == [
        {
            "topic_id": str(scenes["home"]),
            "title": "Doma",
            "line": "Das Haus ist neu.",
            "line_cs": "Ten dům je nový.",
            "match": "Haus",
        },
        {
            "topic_id": str(scenes["crime"]),
            "title": "Detektivka",
            "line": None,
            "line_cs": None,
            "match": None,
        },
    ]
    assert (await client.get(f"/api/v1/words/{ids['gehen']}")).json()["contexts"] == []
    async for db_ in get_session():
        # Current scenes tag the taught word's segment, which also finds inflected forms.
        crime = await db_.get(Scene, scenes["crime"])
        crime.lines = [
            {
                "cs": "Kvůli domu.",
                "segments": [
                    {"t": "Wegen des "},
                    {"t": "Hauses", "item": str(ids["Haus"])},
                    {"t": "."},
                ],
            }
        ]
        await db_.commit()
        break
    tagged = (await client.get(f"/api/v1/words/{ids['Haus']}")).json()["contexts"][1]
    assert (tagged["line"], tagged["line_cs"], tagged["match"]) == (
        "Wegen des Hauses.",
        "Kvůli domu.",
        "Hauses",
    )
    await login(client, "eva", "4321")
    child = (await client.get(f"/api/v1/words/{ids['Haus']}")).json()
    assert [c["title"] for c in child["contexts"]] == ["Doma"]


async def test_word_detail_counts_check_evidence_separately_for_recognition_and_recall(
    db, client, clock
):
    from datetime import date

    from app.models import LearningEvent
    from app.models.learning import TaskType

    me = await setup_parent(client)
    uid = uuid.UUID(me["acting"]["id"])
    ids = await seed(uid, clock)

    def event(task: TaskType, day: int, evidence: bool = True) -> LearningEvent:
        return LearningEvent(
            user_id=uid,
            lexicon_item_id=ids["gehen"],
            task_type=task,
            attempt_no=1,
            answer="x",
            is_correct=evidence,
            verdict="exact" if evidence else "wrong",
            policy_version="v4",
            idempotency_key=uuid.uuid4().hex,
            result={},
            hint_used=False,
            revealed=False,
            counts_as_evidence=evidence,
            answer_mode="typed",
            local_date=date(2026, 1, day),
            occurred_at=clock.now,
        )

    async for db_ in get_session():
        db_.add_all(
            [
                event(TaskType.RECOGNITION, 1),
                event(TaskType.RECOGNITION, 2),
                event(TaskType.RECALL, 2),
                event(TaskType.RECALL, 3, evidence=False),  # practice or a miss: not evidence
            ]
        )
        await db_.commit()
        break
    out = (await client.get(f"/api/v1/words/{ids['gehen']}")).json()["evidence"]
    assert out["recognition"] == {"correct": 3, "days": 2}
    assert out["production"] == {"correct": 1, "days": 1}
    assert out["required_correct"] == 3 and out["production_required_days"] == 2
    none = (await client.get(f"/api/v1/words/{ids['schön']}")).json()["evidence"]
    assert none["recognition"] == {"correct": 0, "days": 0}


async def test_word_list_sorts_by_review_errors_and_recent(db, client, clock):
    from datetime import timedelta

    me = await setup_parent(client)
    uid = uuid.UUID(me["acting"]["id"])
    ids = await seed(uid, clock)
    async for db_ in get_session():
        rows = {
            r.lexicon_item_id: r
            for r in (
                await db_.execute(select(UserWordProgress).where(UserWordProgress.user_id == uid))
            ).scalars()
        }
        rows[ids["gehen"]].next_review_at = clock.now - timedelta(days=1)
        rows[ids["schön"]].next_review_at = clock.now + timedelta(days=3)
        rows[ids["schön"]].error_count = 4
        rows[ids["Mord"]].error_count = 1
        rows[ids["gehen"]].introduced_at = clock.now - timedelta(days=5)
        rows[ids["Haus"]].introduced_at = clock.now - timedelta(days=2)
        await db_.commit()
        break

    async def lemmas(sort: str) -> list[str]:
        out = (await client.get(f"/api/v1/words?language=de&sort={sort}")).json()
        return [w["lemma"] for w in out["items"]]

    assert await lemmas("rank") == ["Haus", "gehen", "schön", "Mord"]
    assert await lemmas("review") == ["gehen", "Haus", "schön", "Mord"]
    assert await lemmas("errors") == ["schön", "Mord", "Haus", "gehen"]
    assert await lemmas("recent") == ["schön", "Mord", "Haus", "gehen"]
    assert (await client.get("/api/v1/words?language=de&sort=nope")).status_code == 422


async def test_status_counts_follow_search_and_due_filters(db, client, clock):
    me = await setup_parent(client)
    await seed(uuid.UUID(me["acting"]["id"]), clock)
    found = (await client.get("/api/v1/words?language=de&q=geh")).json()
    assert found["counts"] == {"mastered": 0, "known": 0, "passive": 1, "learning": 0, "seen": 0}
    due = (await client.get("/api/v1/words?language=de&due=true")).json()
    assert [w["lemma"] for w in due["items"]] == ["Haus"]
    assert sum(due["counts"].values()) == due["total"] == 1
    # The status filter narrows the list but not its own facet counts.
    learning = (await client.get("/api/v1/words?language=de&status=learning")).json()
    assert learning["counts"]["passive"] == 1
    assert learning["total"] == learning["counts"]["learning"]


async def test_word_list_filters_by_word_kind(db, client, clock):
    me = await setup_parent(client)
    await seed(uuid.UUID(me["acting"]["id"]), clock)

    async def lemmas(kind: str) -> list[str]:
        out = (await client.get(f"/api/v1/words?language=de&kind={kind}")).json()
        assert sum(out["counts"].values()) == out["total"]
        return [w["lemma"] for w in out["items"]]

    assert await lemmas("noun") == ["Haus", "Mord"]
    assert await lemmas("verb") == ["gehen"]
    assert await lemmas("adj") == ["schön"]
    assert await lemmas("other") == []
    assert (await client.get("/api/v1/words?language=de&kind=x")).status_code == 422
