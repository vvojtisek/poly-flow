import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.domain.enums import CefrLevel, Language, ProgressState
from app.models.learning import SessionMode, SessionStatus, TaskStatus, TaskType

IdempotencyKey = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_-]{8,64}$")]


class StartIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    language: Language | None = None  # defaults to the profile's active language
    mode: SessionMode = SessionMode.LEARN


class SegmentOut(BaseModel):
    text: str
    item_id: uuid.UUID | None = None  # a lexicon word: tappable for its gloss
    gloss: str | None = None
    new: bool = False  # introduced by this lesson


class SceneLineOut(BaseModel):
    speaker: str | None
    cs: str
    segments: list[SegmentOut]


class SceneOut(BaseModel):
    title: str
    lines: list[SceneLineOut]


class WordCard(BaseModel):
    """A new word, presented before any practice."""

    id: uuid.UUID
    lemma: str
    pos: str
    gender: str | None
    ipa: str | None
    translation: str
    context: str | None  # the scene line with the word, else its example sentence
    context_cs: str | None


class SessionOut(BaseModel):
    id: uuid.UUID
    language: Language
    mode: SessionMode
    status: SessionStatus
    total: int
    remaining: int
    created_at: datetime
    completed_at: datetime | None
    summary: dict
    scene: SceneOut | None = None  # learn only
    words: list[WordCard] = []  # learn only


class StartOut(BaseModel):
    session: SessionOut | None  # None: learn = no new words left; check = nothing due


class Option(BaseModel):
    id: int
    text: str


class TaskOut(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    position: int
    total: int
    type: TaskType
    status: TaskStatus
    attempts: int
    hint_level: int
    is_new_item: bool
    # recognition: the target word; recall: the Czech meaning
    prompt: str
    pos: str
    gender: str | None
    example: str | None  # only for recognition (it would give recall away)
    # recall: the example sentence with the target word blanked, to disambiguate
    # function words ("ten (určitý člen)" alone could be der/die/das).
    cloze: str | None
    options: list[Option] | None
    hint: str | None


class NextOut(BaseModel):
    task: TaskOut | None  # None: every task in the lesson is finished


class AnswerIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    idempotency_key: IdempotencyKey
    choice: int | None = Field(default=None, ge=0)
    text: Annotated[str, StringConstraints(max_length=200)] | None = None


class RevealIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    idempotency_key: IdempotencyKey


class AnswerOut(BaseModel):
    task_id: uuid.UUID
    correct: bool
    verdict: Literal[
        "exact",
        "accepted_variant",
        "case",
        "diacritics",
        "wrong",
        "revealed",
        "spoken",  # a spoken answer whose transcript is the word
        "not_understood",  # a spoken answer the transcript cannot confirm; nothing changed
    ]
    note: str | None
    counted: bool  # contributed evidence toward knowing the word
    attempts: int
    task_done: bool
    can_retry: bool
    expected: str | None
    meaning: str | None
    # Spoken answers: what speech recognition heard (a transcript, not a pronunciation score).
    heard: str | None = None


class BandProgress(BaseModel):
    band: int
    items: int  # lexicon items available in this band
    known: int  # passive and active known


class ProgressOut(BaseModel):
    language: Language
    lexicon_items: int
    seen: int
    by_state: dict[ProgressState, int]
    passive_known: int
    active_known: int
    known: int  # both passive and active
    introduced: int  # presented in a finished lesson
    due_now: int  # introduced words a check can ask about now
    orthography_avg: float | None
    phonetic_measured: int  # profiles start at 0: pronunciation scoring is not validated yet
    grammar_unlocked: bool
    grammar_gate: int
    next_milestone: int | None
    next_milestone_cefr: CefrLevel | None
    by_band: list[BandProgress]
    active_session_id: uuid.UUID | None  # open lesson
    active_check_session_id: uuid.UUID | None
