"""Tap a word while reading: its dictionary entry, if the lexicon has one. Read-only."""

from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.api.deps import DB, Auth
from app.domain.enums import Language
from app.services import lookup as svc

router = APIRouter(prefix="/api/v1/lookup", tags=["words"])


class HitOut(BaseModel):
    id: str
    lemma: str
    translation: str
    gender: str | None
    pos: str
    status: str | None
    note: str | None


@router.get("", response_model=list[HitOut])
async def lookup(
    auth: Auth,
    db: DB,
    word: Annotated[str, Query(min_length=1, max_length=96)],
    language: Annotated[Language | None, Query()] = None,
) -> list[HitOut]:
    hits = await svc.lookup(db, auth.acting, language or auth.acting.active_language, word)
    return [HitOut(**asdict(h)) for h in hits]
