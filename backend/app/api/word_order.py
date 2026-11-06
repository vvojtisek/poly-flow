"""Word order practice: sentences from the scenes and example sentences the profile has met.

Ungraded; nothing is recorded. A sentence is referenced as "s:<scene id>:<line>" (a scene line,
with its Czech translation) or "w:<lexicon item id>" (an example sentence; the Czech meaning of
its word is the hint).
"""

import random
import uuid
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.api.deps import DB, Auth
from app.api.dictation import _pool
from app.api.roleplay import _scenes
from app.domain import roleplay as rp
from app.domain import word_order as wo
from app.domain.enums import Language
from app.models import LexiconItem, User
from app.services.lookup import lookup

router = APIRouter(prefix="/api/v1/word-order", tags=["practice"])


class PuzzleOut(BaseModel):
    ref: str
    tiles: list[str]  # shuffled
    end: str
    cs: str | None  # the Czech sentence (scene lines)
    hint: str | None  # "word = meaning" (example sentences)
    pool: int


class EmptyOut(BaseModel):
    ref: None = None
    pool: int = 0


class CheckIn(BaseModel):
    ref: str = Field(max_length=120)
    order: list[str] = Field(max_length=wo.MAX_TILES)


class CheckOut(BaseModel):
    correct: bool
    marks: list[bool]
    sentence: str
    cs: str | None


async def _sources(
    db, user: User, language: Language
) -> dict[str, tuple[str, str | None, str | None]]:
    """ref → (sentence, Czech sentence, hint) for every usable sentence of this profile."""
    out: dict[str, tuple[str, str | None, str | None]] = {}
    for scene in await _scenes(db, user, language):
        for i, raw in enumerate(scene.lines):
            line = rp.plain(raw)
            if wo.usable(wo.split(line.text)):
                out[f"s:{scene.id}:{i}"] = (line.text, line.cs or None, None)
    for item in (await db.execute(_pool(user, language))).scalars():
        sentence = item.example_sentence or ""
        if wo.usable(wo.split(sentence)):
            out[f"w:{item.id}"] = (sentence, None, f"{item.lemma} = {item.translation_cs}")
    return out


async def _resolve(
    db, user: User, language: Language, ref: str
) -> tuple[str, str | None, str | None]:
    """One sentence by ref, with the same visibility rules as the pool."""
    kind, _, rest = ref.partition(":")
    try:
        if kind == "s":
            sid, _, idx = rest.partition(":")
            scene = next(
                (s for s in await _scenes(db, user, language) if s.id == uuid.UUID(sid)), None
            )
            if scene is not None and 0 <= int(idx) < len(scene.lines):
                line = rp.plain(scene.lines[int(idx)])
                return line.text, line.cs or None, None
        elif kind == "w":
            item = (
                await db.execute(_pool(user, language).where(LexiconItem.id == uuid.UUID(rest)))
            ).scalar_one_or_none()
            if item is not None and item.example_sentence:
                return item.example_sentence, None, f"{item.lemma} = {item.translation_cs}"
    except ValueError:
        pass
    raise HTTPException(404, "sentence_not_found")


async def _puzzle(db, user: User, language: Language, sentence: str) -> wo.Puzzle:
    p = wo.split(sentence)
    first = p.tiles[0]
    if first[:1].isupper() and not (language == "en" and first == "I"):
        if first.lower().rstrip(",") in wo.CLOSED_CLASS.get(language, ()):
            return wo.lower_first(p)
        hits = await lookup(db, user, language, first)
        if hits and all(h.pos not in ("NOUN", "PROPN") for h in hits):
            return wo.lower_first(p)
    return p


@router.get("/next", response_model=PuzzleOut | EmptyOut)
async def next_puzzle(
    auth: Auth,
    db: DB,
    language: Annotated[Language | None, Query()] = None,
    exclude: Annotated[list[str] | None, Query(max_length=50)] = None,
) -> PuzzleOut | EmptyOut:
    lang = language or auth.acting.active_language
    sources = await _sources(db, auth.acting, lang)
    if not sources:
        return EmptyOut()
    refs = [r for r in sources if r not in set(exclude or ())] or list(sources)
    # Scene lines carry a Czech sentence; offer them a little more often.
    weights = [3 if r.startswith("s:") else 1 for r in refs]
    ref = random.choices(refs, weights=weights)[0]
    sentence, cs, hint = sources[ref]
    p = await _puzzle(db, auth.acting, lang, sentence)
    return PuzzleOut(
        ref=ref,
        tiles=wo.shuffled(p.tiles, ref),
        end=p.end,
        cs=cs,
        hint=hint,
        pool=len(sources),
    )


@router.post("/check", response_model=CheckOut)
async def check(
    body: CheckIn, auth: Auth, db: DB, language: Annotated[Language | None, Query()] = None
) -> CheckOut:
    lang = language or auth.acting.active_language
    sentence, cs, _ = await _resolve(db, auth.acting, lang, body.ref)
    p = await _puzzle(db, auth.acting, lang, sentence)
    if not wo.same_words(p.tiles, body.order):
        raise HTTPException(422, "tiles_mismatch")
    m = wo.marks(p.tiles, body.order)
    return CheckOut(correct=all(m), marks=m, sentence=" ".join(sentence.split()), cs=cs)
