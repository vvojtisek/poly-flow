"""Persistent exercise difficulty changes the active vocabulary task format."""

from uuid import UUID

import pytest
from sqlalchemy import select

from app.db.session import get_session
from app.models import LexiconItem, UserWordProgress
from tests.helpers import csrf, seed_words, setup_parent
from tests.test_learning import answer, correct_answer, next_task, overrides, start  # noqa: F401


async def _item_for_prompt(prompt: str) -> LexiconItem:
    async for db in get_session():
        return (
            await db.execute(
                select(LexiconItem).where(
                    (LexiconItem.lemma == prompt) | (LexiconItem.translation_cs == prompt)
                )
            )
        ).scalar_one()
    raise AssertionError("test database session unavailable")


@pytest.mark.parametrize(("difficulty", "option_count"), [("easy", 4), ("medium", 5)])
async def test_manual_mode_adds_word_bank_with_distractors(db, client, difficulty, option_count):
    await seed_words()
    me = await setup_parent(client)
    changed = await client.patch(
        "/api/v1/me/profile",
        json={"settings": {"practice_difficulty": difficulty}},
        headers=csrf(me),
    )
    assert changed.status_code == 200
    assert changed.json()["settings"]["practice_difficulty"] == difficulty

    known_lemmas: set[str] = set()
    if difficulty == "medium":
        async for db_session in get_session():
            user_id = UUID(me["acting"]["id"])
            known_items = (await db_session.execute(select(LexiconItem).limit(8))).scalars().all()
            known_lemmas = {item.lemma for item in known_items}
            db_session.add_all(
                UserWordProgress(user_id=user_id, lexicon_item_id=item.id, passive_known=True)
                for item in known_items
            )
            await db_session.commit()

    session = await start(client, me)
    task = await next_task(client, session["id"])
    while task["type"] == "recognition":
        assert task["options"]
        assert (await answer(client, me, task, await correct_answer(task))).json()["correct"]
        task = await next_task(client, session["id"])
    recall = task
    assert recall["type"] == "recall" and len(recall["options"]) == option_count
    target = await _item_for_prompt(recall["prompt"])
    assert len({option["text"].casefold() for option in recall["options"]}) == option_count
    if known_lemmas:
        distractors = {
            option["text"] for option in recall["options"] if option["text"] != target.lemma
        }
        assert distractors <= known_lemmas
    correct_id = next(
        option["id"] for option in recall["options"] if option["text"] == target.lemma
    )
    graded = await answer(client, me, recall, {"choice": correct_id})
    assert graded.status_code == 200 and graded.json()["correct"], graded.text


async def test_hard_mode_uses_free_answer_for_recognition(db, client):
    await seed_words()
    me = await setup_parent(client)
    changed = await client.patch(
        "/api/v1/me/profile",
        json={"settings": {"practice_difficulty": "hard"}},
        headers=csrf(me),
    )
    assert changed.status_code == 200
    assert changed.json()["settings"]["practice_difficulty"] == "hard"
    session = await start(client, me)
    hard = await next_task(client, session["id"])
    assert hard["type"] == "recognition" and hard["options"] is None
    item = await _item_for_prompt(hard["prompt"])
    graded = await answer(client, me, hard, {"text": item.translation_cs})
    assert graded.status_code == 200 and graded.json()["correct"], graded.text
