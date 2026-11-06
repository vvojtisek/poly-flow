"""Grammar content packs and answer grading (plan P5). Pure parsing, validation, grading; no I/O.

A content pack (`backend/data/grammar/<lang>.grammar.json`) holds the grammar skill tree of one
target language, explained in Czech: units in curriculum order, each with notes, examples and
exercises. Four exercise kinds, all graded on the server:

    choice     pick one option for the gap (der/die/das, a case ending, a preposition)
    gap        type the missing form (a conjugated verb, an ending)
    order      build the sentence from the given tiles
    translate  translate a sentence (cs -> target or target -> cs), several accepted answers

Every exercise carries a Czech explanation of the rule it practises; a wrong answer is
classified (`ErrorTag`) so the mistake engine can name what went wrong.
"""

import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.domain.enums import CefrLevel, ContentFlag, Language
from app.domain.language_packs import PACKS, pack
from app.domain.orthography import normalize

NonEmpty = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
SLUG = r"^[a-z0-9][a-z0-9-]{0,63}$"
LEVELS = (
    CefrLevel.A1,
    CefrLevel.A2,
    CefrLevel.B1,
    CefrLevel.B2,
    CefrLevel.C1,
    CefrLevel.C2,
)

# Grammar lessons are open from the first day (Vlad, 2026-11-05: an A1-B2 path in German needs
# articles, cases and verb endings from the first sentences). The tree only recommends an order.
GRAMMAR_OPEN_FROM_START = True


class ExerciseKind(StrEnum):
    CHOICE = "choice"
    GAP = "gap"
    ORDER = "order"
    TRANSLATE = "translate"


class ErrorTag(StrEnum):
    """What a wrong answer got wrong; the mistake engine aggregates these."""

    ARTICLE = "article"  # wrong article / case form of the article (der/den/dem...)
    ENDING = "ending"  # right stem, wrong ending (verb conjugation, adjective, noun)
    WORD_ORDER = "word_order"  # right words, wrong order (verb second, verb last...)
    CAPITALISATION = "capitalisation"  # German noun written lower-case
    DIACRITICS = "diacritics"  # missing umlaut / accent
    SPELLING = "spelling"  # close to the right word, misspelt
    WORD_CHOICE = "word_choice"  # a different word (preposition, pronoun, verb)
    MEANING = "meaning"  # a word's meaning not recognised (vocabulary)
    GENDER = "gender"  # vocabulary: right noun, wrong article (gender)
    OTHER = "other"


# Articles and determiners whose swap is an article/case error, per language.
DETERMINERS: dict[Language, frozenset[str]] = {lang: p.determiners for lang, p in PACKS.items()}


# ---------------------------------------------------------------- content pack schema


class Example(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: NonEmpty  # target language
    cs: NonEmpty
    variant: Literal["uk", "us"] | None = None  # English example for one explicit locale


class NoteSection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    heading: NonEmpty
    text: NonEmpty  # Czech; "**bold**" marks the key form
    # Optional table: first row is the header.
    table: list[list[str]] | None = None

    @model_validator(mode="after")
    def _rectangular(self) -> "NoteSection":
        if self.table is not None:
            if len(self.table) < 2:
                raise ValueError("a table needs a header and at least one row")
            width = len(self.table[0])
            if any(len(r) != width for r in self.table):
                raise ValueError(f"table rows must all have {width} cells")
        return self


class Exercise(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: Annotated[str, StringConstraints(pattern=SLUG)]
    kind: ExerciseKind
    # choice/gap: a sentence with exactly one "___"; order/translate: the sentence to build or
    # translate (Czech for cs->target, target language for target->cs).
    prompt: NonEmpty
    prompt_cs: str | None = None  # Czech meaning shown with a choice/gap/order sentence
    direction: Literal["cs-target", "target-cs"] | None = None  # translate only
    options: list[NonEmpty] | None = None  # choice only
    tokens: list[NonEmpty] | None = None  # order only: the tiles, in the order shown
    # Accepted answers; the first is the one shown. choice: exactly one, one of `options`.
    answers: list[NonEmpty] = Field(min_length=1)
    # Short Czech explanation of why the answer is right (the tutor's grounding).
    explain: NonEmpty
    content_flags: list[ContentFlag] = Field(default_factory=list)

    @model_validator(mode="after")
    def _shape(self) -> "Exercise":
        k = self.kind
        if k in (ExerciseKind.CHOICE, ExerciseKind.GAP) and self.prompt.count("___") != 1:
            raise ValueError(f"{self.id}: a {k} prompt needs exactly one ___")
        if k == ExerciseKind.CHOICE:
            if not self.options or len(self.options) < 2 or len(self.options) > 6:
                raise ValueError(f"{self.id}: choice needs 2-6 options")
            if len(set(self.options)) != len(self.options):
                raise ValueError(f"{self.id}: duplicate options")
            if len(self.answers) != 1 or self.answers[0] not in self.options:
                raise ValueError(f"{self.id}: choice needs one answer that is an option")
        elif self.options is not None:
            raise ValueError(f"{self.id}: only choice exercises have options")
        if k == ExerciseKind.ORDER:
            if not self.tokens or len(self.tokens) < 2:
                raise ValueError(f"{self.id}: order needs at least 2 tokens")
            tiles = Counter(w.casefold() for w in _words(" ".join(self.tokens)))
            for a in self.answers:
                if Counter(w.casefold() for w in _words(a)) != tiles:
                    raise ValueError(f"{self.id}: answer {a!r} does not use exactly the tokens")
            if _key(" ".join(self.tokens)).casefold() in {_key(a).casefold() for a in self.answers}:
                raise ValueError(f"{self.id}: tokens are already in a correct order")
        elif self.tokens is not None:
            raise ValueError(f"{self.id}: only order exercises have tokens")
        if (k == ExerciseKind.TRANSLATE) != (self.direction is not None):
            raise ValueError(f"{self.id}: direction is required for translate, only there")
        return self


class Unit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: Annotated[str, StringConstraints(pattern=SLUG)]
    level: CefrLevel
    title: NonEmpty  # Czech
    summary: NonEmpty  # short Czech description for lesson discovery
    objective: NonEmpty | None = None  # observable learner outcome; older packs use summary
    notes: list[NoteSection] = Field(min_length=1)
    examples: list[Example] = Field(min_length=1)
    exercises: list[Exercise] = Field(min_length=4)

    @model_validator(mode="after")
    def _kinds(self) -> "Unit":
        if self.level not in LEVELS:
            raise ValueError(f"{self.id}: level must be A1-C2")
        return self


class GrammarPack(BaseModel):
    model_config = ConfigDict(extra="forbid")
    language: Language
    source: NonEmpty  # e.g. "claude-draft"
    license: NonEmpty
    revision: NonEmpty
    review_status: Literal["unreviewed", "reviewed"]
    note: str | None = None
    units: list[Unit] = Field(min_length=1)

    @model_validator(mode="after")
    def _consistent(self) -> "GrammarPack":
        unit_ids = [u.id for u in self.units]
        if len(set(unit_ids)) != len(unit_ids):
            raise ValueError("duplicate unit ids")
        ex_ids = [e.id for u in self.units for e in u.exercises]
        if len(set(ex_ids)) != len(ex_ids):
            raise ValueError("duplicate exercise ids")
        # Curriculum order never goes back a level.
        order = [LEVELS.index(u.level) for u in self.units]
        if order != sorted(order):
            raise ValueError("units must be ordered A1 -> C2")
        return self


# ---------------------------------------------------------------- grading


def _fold(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def _words(text: str) -> list[str]:
    """Words of a sentence, punctuation dropped (kept: apostrophes and hyphens inside words)."""
    text = normalize(text)  # also folds typographic apostrophes
    return re.findall(r"[\w'-]+", text)


def _key(text: str) -> str:
    return " ".join(_words(text))


def _unfallback(language: Language, text: str) -> str:
    """Learner text with keyboard fallbacks (ae, oe, ue, ss) read as the real characters."""
    return pack(language).unfallback(text)


@dataclass(frozen=True, slots=True)
class Graded:
    correct: bool
    verdict: str  # exact | accepted_variant | wrong
    note: str | None = None  # machine key for the UI explanation (cs.feedback.notes)
    error: ErrorTag | None = None
    matched: str | None = None  # the accepted answer the learner's text matched or came close to


def _closest(answer: str, accepted: list[str]) -> str:
    """The accepted answer sharing most words with the learner's; ties: most in place."""
    words = [w.casefold() for w in _words(answer)]
    got = Counter(words)

    def score(a: str) -> tuple[int, int]:
        aw = [w.casefold() for w in _words(a)]
        in_place = sum(x == y for x, y in zip(aw, words, strict=False))
        return sum((got & Counter(aw)).values()), in_place

    return max(accepted, key=score)


def classify(language: Language, expected: str, answer: str) -> ErrorTag:
    """Name the deviation of a wrong answer from the closest accepted answer."""
    exp, got = _words(expected), _words(answer)
    if not got:
        return ErrorTag.OTHER
    fe, fg = [w.casefold() for w in exp], [w.casefold() for w in got]
    if Counter(fe) == Counter(fg):
        if fe != fg:
            return ErrorTag.WORD_ORDER
        return ErrorTag.CAPITALISATION
    if [_fold(w) for w in fe] == [_fold(w) for w in fg]:
        return ErrorTag.DIACRITICS
    if len(fe) == len(fg):
        diffs = [(e, g) for e, g in zip(fe, fg, strict=True) if e != g]
        if len(diffs) == 1:
            e, g = diffs[0]
            dets = DETERMINERS[language]
            if e in dets and g in dets:
                return ErrorTag.ARTICLE
            stem = _common_prefix(e, g)
            if stem >= 3 and stem >= min(len(e), len(g)) - 3:
                return ErrorTag.ENDING
            if _edit_distance(e, g) <= max(1, len(e) // 4):
                return ErrorTag.SPELLING
            return ErrorTag.WORD_CHOICE
    if Counter(fe) - Counter(fg) and sum((Counter(fe) - Counter(fg)).values()) == 1:
        missing = next(iter(Counter(fe) - Counter(fg)))
        if missing in DETERMINERS[language]:
            return ErrorTag.ARTICLE
    return ErrorTag.OTHER


def _common_prefix(a: str, b: str) -> int:
    n = 0
    for x, y in zip(a, b, strict=False):
        if x != y:
            break
        n += 1
    return n


def _edit_distance(a: str, b: str) -> int:
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def _german_nouns_lowered(expected: str, answer: str) -> bool:
    """Same words, but a capitalised word in the answer key is lower-case in the answer."""
    e, a = _words(expected), _words(answer)
    if len(e) != len(a):
        return False
    return all(x.casefold() == y.casefold() for x, y in zip(e, a, strict=True)) and any(
        x != y and x[:1].isupper() and i > 0 for i, (x, y) in enumerate(zip(e, a, strict=True))
    )


def grade(
    language: Language,
    kind: ExerciseKind,
    answers: list[str],
    *,
    text: str | None = None,
    choice: str | None = None,
    case_sensitive_target: bool = True,
) -> Graded:
    """Grade one answer. `choice` is the picked option's text (choice); `text` otherwise.

    `case_sensitive_target`: the answer is in the target language, so German noun
    capitalisation matters (a lower-case noun is wrong, tagged CAPITALISATION). A Czech answer
    (translate target->cs) ignores case and diacritics are still required.
    """
    if kind == ExerciseKind.CHOICE:
        if choice is None:
            raise ValueError("choice required")
        if choice == answers[0]:
            return Graded(True, "exact", matched=answers[0])
        dets = DETERMINERS[language]
        tag = (
            ErrorTag.ARTICLE
            if choice.casefold() in dets and answers[0].casefold() in dets
            else classify(language, answers[0], choice)
        )
        return Graded(False, "wrong", error=tag, matched=answers[0])

    if text is None or not normalize(text):
        return Graded(False, "wrong", error=ErrorTag.OTHER, matched=answers[0])
    got = _key(text)
    keys = {_key(a): a for a in answers}
    if got in keys:
        return Graded(True, "exact", matched=keys[got])
    # Typed without umlauts/ß: accepted with a note (as for single words).
    unfallback = _key(_unfallback(language, text))
    if unfallback in keys:
        return Graded(True, "accepted_variant", note="umlaut_as_e", matched=keys[unfallback])
    folded = {k.casefold(): a for k, a in keys.items()}
    if got.casefold() in folded:
        exp = folded[got.casefold()]
        if (
            case_sensitive_target
            and pack(language).capitalises_nouns
            and _german_nouns_lowered(exp, text)
        ):
            return Graded(
                False, "case", note="de_noun_capital", error=ErrorTag.CAPITALISATION, matched=exp
            )
        return Graded(True, "exact", matched=exp)  # sentence-initial capital is not significant
    if not case_sensitive_target:
        # A Czech answer: free word order, and a missing háček/čárka is accepted with a note.
        bag = Counter(w.casefold() for w in _words(text))
        for a in answers:
            if Counter(w.casefold() for w in _words(a)) == bag:
                return Graded(True, "exact", matched=a)
        fbag = Counter(_fold(w.casefold()) for w in _words(text))
        for a in answers:
            if Counter(_fold(w.casefold()) for w in _words(a)) == fbag:
                return Graded(True, "accepted_variant", note="cs_diacritics", matched=a)
    closest = _closest(text, answers)
    return Graded(False, "wrong", error=classify(language, closest, text), matched=closest)


def blank(prompt: str, answer: str) -> str:
    """The sentence with the gap filled in, without a trailing hint such as "(sein)"."""
    filled = prompt.replace("___", answer, 1)
    return re.sub(r"\s*\([^()]*\)\s*$", "", filled)
