"""Private word collections limited to words a learner has already encountered."""

import uuid

from sqlalchemy import case, delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import Language
from app.models import LexiconItem, User, UserWordProgress, WordCollection, WordCollectionItem
from app.services.learning import LearningError, _suitable


def clean_name(name: str) -> str:
    return " ".join(name.split())


async def list_collections(db: AsyncSession, user: User, language: Language) -> list[dict]:
    visible_word_id = case(
        (
            (LexiconItem.language == language)
            & UserWordProgress.lexicon_item_id.is_not(None)
            & _suitable(user),
            LexiconItem.id,
        )
    )
    stmt = (
        select(WordCollection, func.count(visible_word_id))
        .outerjoin(WordCollectionItem, WordCollectionItem.collection_id == WordCollection.id)
        .outerjoin(LexiconItem, LexiconItem.id == WordCollectionItem.lexicon_item_id)
        .outerjoin(
            UserWordProgress,
            (UserWordProgress.lexicon_item_id == LexiconItem.id)
            & (UserWordProgress.user_id == user.id),
        )
        .where(WordCollection.user_id == user.id, WordCollection.language == language)
        .group_by(WordCollection.id)
        .order_by(WordCollection.created_at, WordCollection.id)
    )
    return [
        {"id": row.id, "name": row.name, "count": count, "created_at": row.created_at}
        for row, count in (await db.execute(stmt)).all()
    ]


async def create_collection(
    db: AsyncSession, user: User, language: Language, name: str
) -> WordCollection:
    clean = clean_name(name)
    if not clean or len(clean) > 60:
        raise LearningError("invalid_collection_name", 422)
    collection = WordCollection(user_id=user.id, language=language, name=clean)
    db.add(collection)
    await db.flush()
    return collection


async def rename_collection(
    db: AsyncSession, user: User, collection_id: uuid.UUID, name: str
) -> WordCollection:
    clean = clean_name(name)
    if not clean or len(clean) > 60:
        raise LearningError("invalid_collection_name", 422)
    collection = await db.scalar(
        select(WordCollection).where(
            WordCollection.id == collection_id, WordCollection.user_id == user.id
        )
    )
    if collection is None:
        raise LearningError("collection_not_found", 404)
    collection.name = clean
    await db.flush()
    return collection


async def get_collection(
    db: AsyncSession, user: User, collection_id: uuid.UUID
) -> tuple[WordCollection, list[dict]]:
    collection = await db.scalar(
        select(WordCollection).where(
            WordCollection.id == collection_id, WordCollection.user_id == user.id
        )
    )
    if collection is None:
        raise LearningError("collection_not_found", 404)
    rows = await db.execute(
        select(
            LexiconItem.id,
            LexiconItem.lemma,
            LexiconItem.gender,
            LexiconItem.pos,
            LexiconItem.translation_cs,
            LexiconItem.frequency_rank,
            LexiconItem.example_sentence,
        )
        .join(WordCollectionItem, WordCollectionItem.lexicon_item_id == LexiconItem.id)
        .join(UserWordProgress, UserWordProgress.lexicon_item_id == LexiconItem.id)
        .where(
            WordCollectionItem.collection_id == collection.id,
            UserWordProgress.user_id == user.id,
            LexiconItem.language == collection.language,
            _suitable(user),
        )
        .order_by(LexiconItem.frequency_rank, LexiconItem.lemma)
    )
    items = [
        {
            "id": r.id,
            "lemma": r.lemma,
            "gender": r.gender,
            "pos": r.pos,
            "translation": r.translation_cs,
            "rank": r.frequency_rank,
            "example": r.example_sentence,
        }
        for r in rows
    ]
    return collection, items


async def add_word(
    db: AsyncSession, user: User, collection_id: uuid.UUID, item_id: uuid.UUID
) -> None:
    collection = await db.scalar(
        select(WordCollection).where(
            WordCollection.id == collection_id, WordCollection.user_id == user.id
        )
    )
    if collection is None:
        raise LearningError("collection_not_found", 404)
    learned = await db.scalar(
        select(LexiconItem.id)
        .join(UserWordProgress, UserWordProgress.lexicon_item_id == LexiconItem.id)
        .where(
            LexiconItem.id == item_id,
            LexiconItem.language == collection.language,
            UserWordProgress.user_id == user.id,
            _suitable(user),
        )
    )
    if learned is None:
        raise LearningError("word_not_found", 404)
    stmt = insert(WordCollectionItem).values(collection_id=collection.id, lexicon_item_id=item_id)
    await db.execute(stmt.on_conflict_do_nothing())


async def add_words(
    db: AsyncSession, user: User, collection_id: uuid.UUID, item_ids: list[uuid.UUID]
) -> int:
    collection = await db.scalar(
        select(WordCollection).where(
            WordCollection.id == collection_id, WordCollection.user_id == user.id
        )
    )
    if collection is None:
        raise LearningError("collection_not_found", 404)
    unique_ids = list(dict.fromkeys(item_ids))
    learned = set(
        (
            await db.scalars(
                select(LexiconItem.id)
                .join(UserWordProgress, UserWordProgress.lexicon_item_id == LexiconItem.id)
                .where(
                    LexiconItem.id.in_(unique_ids),
                    LexiconItem.language == collection.language,
                    UserWordProgress.user_id == user.id,
                    _suitable(user),
                )
            )
        ).all()
    )
    if learned != set(unique_ids):
        raise LearningError("word_not_found", 404)
    stmt = insert(WordCollectionItem).values(
        [{"collection_id": collection.id, "lexicon_item_id": item_id} for item_id in unique_ids]
    )
    result = await db.execute(stmt.on_conflict_do_nothing())
    return result.rowcount or 0


async def remove_word(
    db: AsyncSession, user: User, collection_id: uuid.UUID, item_id: uuid.UUID
) -> None:
    exists = await db.scalar(
        select(WordCollection.id).where(
            WordCollection.id == collection_id, WordCollection.user_id == user.id
        )
    )
    if exists is None:
        raise LearningError("collection_not_found", 404)
    await db.execute(
        delete(WordCollectionItem).where(
            WordCollectionItem.collection_id == collection_id,
            WordCollectionItem.lexicon_item_id == item_id,
        )
    )


async def delete_collection(db: AsyncSession, user: User, collection_id: uuid.UUID) -> None:
    result = await db.execute(
        delete(WordCollection).where(
            WordCollection.id == collection_id, WordCollection.user_id == user.id
        )
    )
    if result.rowcount == 0:
        raise LearningError("collection_not_found", 404)
