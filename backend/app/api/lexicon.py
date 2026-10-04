"""Shared content management (admin). Learners read lexicon items only through lessons."""

import uuid
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from app.api.deps import DB, Manager
from app.domain.enums import Language
from app.models import LexiconItem
from app.schemas.lexicon import LexiconItemOut, LexiconItemUpdate

router = APIRouter(prefix="/api/v1/lexicon", tags=["lexicon"])


@router.get("", response_model=list[LexiconItemOut])
async def list_items(
    _: Manager,
    db: DB,
    language: Language,
    flagged: bool | None = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[LexiconItem]:
    q = select(LexiconItem).where(LexiconItem.language == language)
    if flagged is not None:
        has_flags = func.cardinality(LexiconItem.content_flags) > 0
        q = q.where(has_flags if flagged else ~has_flags)
    q = q.order_by(LexiconItem.frequency_rank).offset(offset).limit(limit)
    return list((await db.execute(q)).scalars())


@router.patch("/{item_id}", response_model=LexiconItemOut)
async def update_item(
    item_id: uuid.UUID, body: LexiconItemUpdate, _: Manager, db: DB
) -> LexiconItem:
    item = await db.get(LexiconItem, item_id)
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "item_not_found")
    changes = body.model_dump(exclude_unset=True)
    if "translation_cs" in changes and changes["translation_cs"] is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "translation_required")
    for field, value in changes.items():
        if field == "content_flags":
            value = sorted({f.value for f in value or []})
        elif value == "":
            value = None  # blank optional text clears the field
        setattr(item, field, value)
    await db.commit()
    return item
