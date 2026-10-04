"""Lessons open with a scene that introduces their words in context (policy v2)."""

import pytest
from sqlalchemy import update

from app.api.deps import get_limiter
from app.api.learning import get_now
from app.cli import RowError, upsert_scenes
from app.db.session import get_session
from app.domain.scenes import SceneFile
from app.main import app
from app.models import LexiconItem
from app.services.rate_limit import MemoryAttemptLimiter
from tests.helpers import Clock, seed_words
from tests.test_learning import child_session, finish, next_task, progress_rows, start

WORDS = [
    ("ich", "PRON", "já"),
    ("sein", "AUX", "být"),
    ("heißen", "VERB", "jmenovat se"),
    ("du", "PRON", "ty"),
    ("Hund", "NOUN", "pes"),
    ("klein", "ADJ", "malý"),
    ("Haus", "NOUN", "dům"),
]

SCENES = {
    "language": "de",
    "revision": "test",
    "scenes": [
        {
            "slug": "hallo",
            "title_cs": "Ahoj",
            "words": ["ich", "heißen", "sein", "du", "klein"],
            "lines": [
                {
                    "speaker": "Anna",
                    "text": "Hallo! [Ich|ich] [heiße|heißen] Anna.",
                    "cs": "Ahoj! Jmenuji se Anna.",
                },
                {
                    "speaker": "Tom",
                    "text": "[Ich|ich] [bin|sein] Tom. Und [du]?",
                    "cs": "Já jsem Tom. A ty?",
                },
                {"speaker": "Anna", "text": "[Ich|ich] [bin|sein] [klein].", "cs": "Jsem malá."},
            ],
        },
        {
            "slug": "hund",
            "title_cs": "Pes",
            "words": ["Hund"],
            "lines": [
                {"text": "Das ist mein [Hund].", "cs": "To je můj pes."},
                {"text": "Er [ist|sein] [klein].", "cs": "Je malý."},
            ],
        },
    ],
}


@pytest.fixture(autouse=True)
def overrides():
    clock = Clock()
    lim = MemoryAttemptLimiter()
    app.dependency_overrides[get_now] = lambda: clock.now
    app.dependency_overrides[get_limiter] = lambda: lim
    yield clock
    app.dependency_overrides.clear()


async def seed(scenes=SCENES) -> None:
    await seed_words(words=WORDS)
    await upsert_scenes(SceneFile.model_validate(scenes))


async def test_lesson_opens_with_scene_and_word_cards(db, client):
    await seed()
    me = await child_session(client)
    s = await start(client, me)
    assert s["mode"] == "learn" and s["total"] == 8
    scene = s["scene"]
    assert scene["title"] == "Ahoj" and len(scene["lines"]) == 3
    first = scene["lines"][0]
    assert first["speaker"] == "Anna" and first["cs"] == "Ahoj! Jmenuji se Anna."
    assert "".join(seg["text"] for seg in first["segments"]) == "Hallo! Ich heiße Anna."
    heisse = next(seg for seg in first["segments"] if seg["text"] == "heiße")
    assert heisse["gloss"] == "jmenovat se" and heisse["new"]
    # The first four words of the scene, in scene order; "klein" waits for the next lesson.
    cards = s["words"]
    assert [c["lemma"] for c in cards] == ["ich", "heißen", "sein", "du"]
    sein = cards[2]
    assert sein["translation"] == "být" and sein["context"] == "Ich bin Tom. Und du?"
    assert sein["context_cs"] == "Já jsem Tom. A ty?"
    klein = next(seg for seg in scene["lines"][2]["segments"] if seg["text"] == "klein")
    assert klein["gloss"] == "malý" and not klein["new"]
    t = await next_task(client, s["id"])
    assert t["type"] == "recognition" and t["prompt"] == "ich"


async def test_scene_continues_then_moves_on(db, client):
    await seed()
    me = await child_session(client)
    await finish(client, me, await start(client, me))
    second = await start(client, me)
    assert second["scene"]["title"] == "Ahoj" and [c["lemma"] for c in second["words"]] == ["klein"]
    await finish(client, me, second)
    third = await start(client, me)
    assert third["scene"]["title"] == "Pes" and [c["lemma"] for c in third["words"]] == ["Hund"]
    await finish(client, me, third)
    # Words without a scene follow by frequency, with no scene to show.
    fourth = await start(client, me)
    assert fourth["scene"] is None and [c["lemma"] for c in fourth["words"]] == ["Haus"]
    assert (await progress_rows())["Hund"].introduced_at is not None


async def test_reimport_moves_words_and_updates_text(db, client):
    await seed()
    moved = {
        **SCENES,
        "scenes": [
            {**SCENES["scenes"][0], "words": ["ich", "heißen", "sein", "du"]},
            {**SCENES["scenes"][1], "title_cs": "Malý pes", "words": ["Hund", "klein"]},
        ],
    }
    await upsert_scenes(SceneFile.model_validate(moved))
    me = await child_session(client)
    await finish(client, me, await start(client, me))
    nxt = await start(client, me)
    assert nxt["scene"]["title"] == "Malý pes"
    assert [c["lemma"] for c in nxt["words"]] == ["Hund", "klein"]


@pytest.mark.parametrize(
    ("change", "error"),
    [
        ({"words": ["ich", "Katze"]}, "word Katze not in lexicon"),
        ({"words": ["ich", "Haus"]}, "word Haus is never [marked]"),
    ],
)
async def test_invalid_scene_is_rejected(db, change, error):
    await seed_words(words=WORDS)
    bad = {**SCENES, "scenes": [{**SCENES["scenes"][0], **change}]}
    with pytest.raises(RowError, match=error.replace("[", r"\[").replace("]", r"\]")):
        await upsert_scenes(SceneFile.model_validate(bad))


async def test_child_skips_a_scene_with_a_flagged_word(db, client):
    await seed()
    async for session in get_session():
        await session.execute(
            update(LexiconItem)
            .where(LexiconItem.lemma == "klein")
            .values(content_flags=["violence"])
        )
        await session.commit()
    me = await child_session(client)  # a child profile
    s = await start(client, me)
    # "hallo" introduces the flagged word, so the child starts with "hund"; no lesson shows it.
    assert s["scene"]["title"] == "Pes"
    assert "klein" not in [c["lemma"] for c in s["words"]]
