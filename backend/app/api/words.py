"""My dictionary: the profile's own words with state, history and audio."""

import uuid
from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError

from app.api.deps import DB, Auth
from app.api.learning import AUDIO_RESPONSES, Now, TtsDep, _chosen_voice, _speech
from app.domain import export
from app.domain.enums import Language
from app.services import notes
from app.services import word_collections as collections
from app.services import words as svc
from app.services.learning import LearningError

router = APIRouter(prefix="/api/v1/words", tags=["learning"])
Status = Literal["mastered", "known", "passive", "learning", "seen"]


class WordRowOut(BaseModel):
    id: uuid.UUID
    lemma: str
    gender: str | None
    pos: str
    rank: int
    translation: str
    status: Status
    due: bool
    next_review_at: datetime | None
    correct: int
    errors: int


class WordListOut(BaseModel):
    total: int
    counts: dict[str, int]
    items: list[WordRowOut]


class WordLevelOut(BaseModel):
    key: str  # CEFR value (indicative, by frequency rank) or "extension" past the C1 band
    first_rank: int
    last_rank: int | None
    total: int  # words of this level the profile gets (content filter applied)
    mine: int  # of those, words the profile has met


class WordTopicOut(BaseModel):
    id: uuid.UUID
    title: str
    total: int
    mine: int


class WordGroupsOut(BaseModel):
    levels: list[WordLevelOut]
    topics: list[WordTopicOut]


class DeckCardOut(BaseModel):
    id: uuid.UUID
    lemma: str
    gender: str | None
    pos: str
    rank: int
    translation: str
    example: str | None
    status: Status
    due: bool


class DeckOut(BaseModel):
    total: int  # own words in the scope; `items` holds at most 50, due and unfinished first
    items: list[DeckCardOut]


class HistoryOut(BaseModel):
    at: datetime
    correct: bool
    graded: bool
    task: str
    mode: str
    error_tag: str | None


class WordContextOut(BaseModel):
    topic_id: uuid.UUID
    title: str
    line: str | None  # the scene line that uses the word as written; None when only inflected
    line_cs: str | None
    match: str | None  # the word as it appears in `line` (may be inflected), for highlighting


class EvidenceTallyOut(BaseModel):
    correct: int  # first-try, hint-free correct check answers
    days: int  # distinct local days with such an answer


class WordEvidenceOut(BaseModel):
    """Check evidence toward the two separate knowledge states and their thresholds."""

    recognition: EvidenceTallyOut  # any correct check answer (production also shows recognition)
    production: EvidenceTallyOut  # correct written or spoken recall only
    required_correct: int
    required_days: int
    production_required_correct: int
    production_required_days: int


class WordDetailOut(BaseModel):
    id: uuid.UUID
    language: Language
    lemma: str
    gender: str | None
    pos: str
    rank: int
    translation: str
    ipa: str | None
    example: str | None
    review_status: str | None
    status: Status
    passive_known: bool
    active_known: bool
    correct: int
    errors: int
    introduced_at: datetime | None
    introduced_by: str | None
    last_reviewed_at: datetime | None
    next_review_at: datetime | None
    review_streak: int
    history: list[HistoryOut]
    note: str | None = None  # the learner's own memory hook
    contexts: list[WordContextOut] = []  # lesson scenes that teach the word
    evidence: WordEvidenceOut


class NoteIn(BaseModel):
    text: str = Field(max_length=1000)  # trimmed to 280 after collapsing whitespace


class NoteOut(BaseModel):
    note: str | None


class CollectionIn(BaseModel):
    language: Language
    name: str = Field(min_length=1, max_length=60)


class CollectionRenameIn(BaseModel):
    name: str = Field(min_length=1, max_length=60)


class CollectionOut(BaseModel):
    id: uuid.UUID
    name: str
    count: int
    created_at: datetime


class CollectionItemOut(BaseModel):
    id: uuid.UUID
    lemma: str
    gender: str | None
    pos: str
    translation: str
    rank: int
    example: str | None


class CollectionDetailOut(BaseModel):
    id: uuid.UUID
    language: Language
    name: str
    items: list[CollectionItemOut]


class CollectionWordIn(BaseModel):
    item_id: uuid.UUID


class CollectionWordsIn(BaseModel):
    item_ids: list[uuid.UUID] = Field(min_length=1, max_length=100)


class CollectionWordsOut(BaseModel):
    added: int


def _http(exc: LearningError) -> HTTPException:
    return HTTPException(exc.status, exc.code)


@router.get("", response_model=WordListOut)
async def list_words(
    auth: Auth,
    db: DB,
    now: Now,
    language: Annotated[Language | None, Query()] = None,
    q: Annotated[str | None, Query(max_length=64)] = None,
    status: Status | None = None,
    due: bool = False,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=200)] = 60,
    level: Annotated[str | None, Query(max_length=16)] = None,
    topic: uuid.UUID | None = None,
    sort: Literal["rank", "review", "errors", "recent"] = "rank",
) -> WordListOut:
    try:
        out = await svc.list_words(
            db,
            auth.acting,
            language or auth.acting.active_language,
            now,
            q=q,
            status=status,
            due=due,
            offset=offset,
            limit=limit,
            level=level,
            topic=topic,
            sort=sort,
        )
    except LearningError as exc:
        raise _http(exc) from exc
    return WordListOut(**out)


@router.get("/groups", response_model=WordGroupsOut)
async def word_groups(
    auth: Auth, db: DB, language: Annotated[Language | None, Query()] = None
) -> WordGroupsOut:
    """Vocabulary by level and by lesson topic, with how many of the words the profile has met."""
    out = await svc.word_groups(db, auth.acting, language or auth.acting.active_language)
    return WordGroupsOut(**out)


@router.get("/deck", response_model=DeckOut)
async def word_deck(
    auth: Auth,
    db: DB,
    now: Now,
    language: Annotated[Language | None, Query()] = None,
    level: Annotated[str | None, Query(max_length=16)] = None,
    topic: uuid.UUID | None = None,
    weak: bool = False,
) -> DeckOut:
    """Flashcards from the profile's own words in one level, one topic, or its unresolved check
    mistakes (`weak=true`); exactly one scope.

    Practice only: flipping and marking cards is not recorded and does not change progress.
    """
    try:
        out = await svc.word_deck(
            db,
            auth.acting,
            language or auth.acting.active_language,
            now,
            level=level,
            topic=topic,
            weak=weak,
        )
    except LearningError as exc:
        raise _http(exc) from exc
    return DeckOut(**out)


@router.get("/export", response_class=Response)
async def export_words(
    auth: Auth,
    db: DB,
    language: Annotated[Language | None, Query()] = None,
    format: Annotated[export.Format, Query()] = "csv",
) -> Response:
    """The acting profile's own words as a download: a spreadsheet CSV or an Anki import file."""
    lang = language or auth.acting.active_language
    rows = await svc.export_rows(db, auth.acting, lang)
    if format == "anki":
        body, media, ext = export.to_anki(rows, lang), "text/tab-separated-values", "txt"
    else:
        body, media, ext = export.to_csv(rows), "text/csv", "csv"
    name = f"polyflow-{lang}-{'anki' if format == 'anki' else 'words'}.{ext}"
    return Response(
        body,
        media_type=f"{media}; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{name}"',
            "Cache-Control": "no-store",
        },
    )


@router.get("/collections/{collection_id}/export", response_class=Response)
async def export_collection(
    collection_id: uuid.UUID,
    auth: Auth,
    db: DB,
    format: Annotated[export.Format, Query()] = "csv",
) -> Response:
    try:
        language, rows = await svc.export_collection_rows(db, auth.acting, collection_id)
    except LearningError as exc:
        raise _http(exc) from exc
    if format == "anki":
        body, media, ext = export.to_anki(rows, language), "text/tab-separated-values", "txt"
    else:
        body, media, ext = export.to_csv(rows), "text/csv", "csv"
    name = f"polyflow-{language}-collection-{collection_id}.{ext}"
    return Response(
        body,
        media_type=f"{media}; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{name}"',
            "Cache-Control": "no-store",
        },
    )


@router.get("/collections", response_model=list[CollectionOut])
async def list_collections(
    auth: Auth,
    db: DB,
    language: Annotated[Language | None, Query()] = None,
) -> list[CollectionOut]:
    rows = await collections.list_collections(
        db, auth.acting, language or auth.acting.active_language
    )
    return [CollectionOut(**row) for row in rows]


@router.post("/collections", response_model=CollectionOut, status_code=201)
async def create_collection(body: CollectionIn, auth: Auth, db: DB) -> CollectionOut:
    try:
        item = await collections.create_collection(db, auth.acting, body.language, body.name)
        await db.flush()
        await db.commit()
    except LearningError as exc:
        raise _http(exc) from exc
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(409, "collection_name_exists") from exc
    return CollectionOut(id=item.id, name=item.name, count=0, created_at=item.created_at)


@router.get("/collections/{collection_id}", response_model=CollectionDetailOut)
async def collection_detail(collection_id: uuid.UUID, auth: Auth, db: DB) -> CollectionDetailOut:
    try:
        item, words = await collections.get_collection(db, auth.acting, collection_id)
    except LearningError as exc:
        raise _http(exc) from exc
    return CollectionDetailOut(id=item.id, language=item.language, name=item.name, items=words)


@router.put("/collections/{collection_id}", response_model=CollectionOut)
async def rename_collection(
    collection_id: uuid.UUID, body: CollectionRenameIn, auth: Auth, db: DB
) -> CollectionOut:
    try:
        item = await collections.rename_collection(db, auth.acting, collection_id, body.name)
        await db.commit()
    except LearningError as exc:
        raise _http(exc) from exc
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(409, "collection_name_exists") from exc
    return CollectionOut(id=item.id, name=item.name, count=0, created_at=item.created_at)


@router.post("/collections/{collection_id}/items", status_code=204)
async def add_collection_word(
    collection_id: uuid.UUID, body: CollectionWordIn, auth: Auth, db: DB
) -> Response:
    try:
        await collections.add_word(db, auth.acting, collection_id, body.item_id)
        await db.commit()
    except LearningError as exc:
        raise _http(exc) from exc
    return Response(status_code=204)


@router.post("/collections/{collection_id}/items/bulk", response_model=CollectionWordsOut)
async def add_collection_words(
    collection_id: uuid.UUID, body: CollectionWordsIn, auth: Auth, db: DB
) -> CollectionWordsOut:
    try:
        added = await collections.add_words(db, auth.acting, collection_id, body.item_ids)
        await db.commit()
    except LearningError as exc:
        await db.rollback()
        raise _http(exc) from exc
    return CollectionWordsOut(added=added)


@router.delete("/collections/{collection_id}/items/{item_id}", status_code=204)
async def remove_collection_word(
    collection_id: uuid.UUID, item_id: uuid.UUID, auth: Auth, db: DB
) -> Response:
    try:
        await collections.remove_word(db, auth.acting, collection_id, item_id)
        await db.commit()
    except LearningError as exc:
        raise _http(exc) from exc
    return Response(status_code=204)


@router.delete("/collections/{collection_id}", status_code=204)
async def delete_collection(collection_id: uuid.UUID, auth: Auth, db: DB) -> Response:
    try:
        await collections.delete_collection(db, auth.acting, collection_id)
        await db.commit()
    except LearningError as exc:
        raise _http(exc) from exc
    return Response(status_code=204)


@router.get("/{item_id}", response_model=WordDetailOut)
async def word(item_id: uuid.UUID, auth: Auth, db: DB, now: Now) -> WordDetailOut:
    try:
        out = WordDetailOut(**await svc.word_detail(db, auth.acting, item_id, now))
    except LearningError as exc:
        raise _http(exc) from exc
    out.note = (await notes.notes_for(db, auth.acting.id, [item_id])).get(item_id)
    return out


@router.put("/{item_id}/note", response_model=NoteOut)
async def put_note(item_id: uuid.UUID, body: NoteIn, auth: Auth, db: DB) -> NoteOut:
    """Set or (with empty text) remove the learner's memory hook for a word."""
    try:
        note = await notes.set_note(db, auth.acting, item_id, body.text)
    except LearningError as exc:
        raise _http(exc) from exc
    await db.commit()
    return NoteOut(note=note)


@router.get("/{item_id}/audio", response_class=FileResponse, responses=AUDIO_RESPONSES)
async def word_audio(
    item_id: uuid.UUID,
    auth: Auth,
    db: DB,
    tts: TtsDep,
    part: Annotated[Literal["word", "example"], Query()] = "word",
) -> FileResponse:
    try:
        language, text = await svc.audio_text(db, auth.acting, item_id, part)
    except LearningError as exc:
        raise _http(exc) from exc
    return await _speech(tts, language, text, _chosen_voice(auth.acting, language))
