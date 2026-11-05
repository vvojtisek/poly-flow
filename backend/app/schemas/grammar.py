import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.domain.enums import CefrLevel, Language
from app.schemas.learning import IdempotencyKey

UnitState = Literal["new", "studied", "known", "mastered"]


class NoteOut(BaseModel):
    heading: str
    text: str
    table: list[list[str]] | None = None


class ExampleOut(BaseModel):
    text: str
    cs: str


class UnitSummaryOut(BaseModel):
    id: str
    level: CefrLevel
    title: str
    summary: str
    status: UnitState
    exercises: int
    due: bool  # studied and due for a grammar check now
    recent_errors: int  # check mistakes in the remediation window
    next_review_at: datetime | None


class LevelOut(BaseModel):
    level: CefrLevel
    units: list[UnitSummaryOut]


class TreeOut(BaseModel):
    language: Language
    open: bool
    due: int
    recommended: str | None
    review_status: Literal["unreviewed", "reviewed", "mixed"] | None
    levels: list[LevelOut]
    active_lesson_unit: str | None
    active_check_session_id: uuid.UUID | None


class UnitOut(BaseModel):
    id: str
    level: CefrLevel
    title: str
    summary: str
    notes: list[NoteOut]
    examples: list[ExampleOut]
    status: UnitState
    review_status: str
    source: str


class ExerciseOut(BaseModel):
    """One exercise as the learner sees it: never the accepted answers while it is open."""

    item_id: uuid.UUID
    session_id: uuid.UUID
    position: int
    total: int
    kind: Literal["choice", "gap", "order", "translate"]
    prompt: str
    prompt_cs: str | None
    direction: Literal["cs-target", "target-cs"] | None
    options: list[str] | None
    tokens: list[str] | None
    unit_id: str
    unit_title: str
    is_remediation: bool
    status: Literal["pending", "done", "revealed"]
    attempts: int


class GrammarSessionOut(BaseModel):
    id: uuid.UUID
    language: Language
    mode: Literal["learn", "check"]
    status: Literal["active", "completed"]
    unit: UnitOut | None
    total: int
    remaining: int
    summary: dict


class GrammarStartOut(BaseModel):
    session: GrammarSessionOut | None


class GrammarNextOut(BaseModel):
    item: ExerciseOut | None


class GrammarCheckIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    language: Language | None = None


class GrammarAnswerIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    idempotency_key: IdempotencyKey
    choice: int | None = Field(default=None, ge=0)
    text: Annotated[str, StringConstraints(max_length=300)] | None = None


class GrammarRevealIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    idempotency_key: IdempotencyKey


class GrammarAnswerOut(BaseModel):
    item_id: uuid.UUID
    correct: bool
    verdict: str
    note: str | None
    error: str | None
    counted: bool
    attempts: int
    task_done: bool
    can_retry: bool
    expected: str | None
    solution: str | None
    explanation: str | None
    unit_id: str
    unit_title: str
