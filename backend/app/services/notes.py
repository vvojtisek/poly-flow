"""Word notes (memory hooks): read and write a profile's own note for a word."""

import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import LearningTask, LexiconItem, User, WordNote
from app.models.word_note import MAX_NOTE
from app.services.learning import LearningError, _suitable


def clean(text: str) -> str:
    """Collapse whitespace; the stored note is one short paragraph."""
    return " ".join(text.split())[:MAX_NOTE]


async def set_note(db: AsyncSession, user: User, item_id: uuid.UUID, text: str) -> str | None:
    """Store (or with empty text delete) the note. Any word this profile may see can carry one."""
    ok = await db.scalar(select(LexiconItem.id).where(LexiconItem.id == item_id, _suitable(user)))
    if ok is None:
        raise LearningError("word_not_found", 404)
    note = clean(text)
    if not note:
        await db.execute(
            delete(WordNote).where(WordNote.user_id == user.id, WordNote.lexicon_item_id == item_id)
        )
        return None
    stmt = insert(WordNote).values(user_id=user.id, lexicon_item_id=item_id, text=note)
    await db.execute(
        stmt.on_conflict_do_update(
            index_elements=[WordNote.user_id, WordNote.lexicon_item_id],
            set_={"text": stmt.excluded.text, "updated_at": func.now()},
        )
    )
    return note


async def notes_for(
    db: AsyncSession, user_id: uuid.UUID, item_ids: list[uuid.UUID]
) -> dict[uuid.UUID, str]:
    if not item_ids:
        return {}
    rows = await db.execute(
        select(WordNote.lexicon_item_id, WordNote.text).where(
            WordNote.user_id == user_id, WordNote.lexicon_item_id.in_(item_ids)
        )
    )
    return dict(rows.all())


async def note_for_task(db: AsyncSession, user: User, task_id: uuid.UUID) -> str | None:
    return await db.scalar(
        select(WordNote.text)
        .join(LearningTask, LearningTask.lexicon_item_id == WordNote.lexicon_item_id)
        .where(LearningTask.id == task_id, WordNote.user_id == user.id)
    )
