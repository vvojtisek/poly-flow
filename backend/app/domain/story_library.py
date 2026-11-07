"""Curated graded stories (`data/stories/*.json`). Pure parsing and validation; no I/O.

Each story is a short, humorous text at one CEFR level (A1-B2), written as ~95% vocabulary of that
level and ~5% "stretch" words from the level above. The stretch words are listed with a Czech
gloss and must appear in the text, so a learner can meet them with context and a gloss.

The same `slug` and `level` exist in every language (one plot, adapted per language). The files
are drafted without native-speaker review: `review_status` stays `unreviewed` until someone
signs the text off, and nothing here may be shown as reviewed fact before then.
"""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.domain.enums import CefrLevel, Language
from app.domain.stories import Question, tokens

NonEmpty = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
SLUG = r"^[a-z0-9][a-z0-9-]{0,63}$"

STORY_LEVELS: tuple[CefrLevel, ...] = (CefrLevel.A1, CefrLevel.A2, CefrLevel.B1, CefrLevel.B2)
STORIES_PER_LEVEL = 10
MAX_STRETCH_SHARE = 0.10  # stretch tokens / all tokens; the aim is about 5%


class StoryLine(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    speaker: str | None = None
    text: NonEmpty
    cs: NonEmpty


class StretchWord(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    word: NonEmpty  # surface form exactly as it appears in the text
    cs: NonEmpty


class LibraryStory(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    slug: Annotated[str, StringConstraints(pattern=SLUG)]
    level: CefrLevel
    title: NonEmpty
    title_cs: NonEmpty
    lines: list[StoryLine] = Field(min_length=6, max_length=16)
    stretch: list[StretchWord] = Field(min_length=1, max_length=8)
    questions: list[Question] = Field(min_length=2, max_length=4)

    @model_validator(mode="after")
    def _level_in_range(self) -> "LibraryStory":
        if self.level not in STORY_LEVELS:
            raise ValueError(f"level must be one of {[x.value for x in STORY_LEVELS]}")
        return self

    def token_list(self) -> list[str]:
        return [t.casefold() for line in self.lines for t in tokens(line.text)]

    def stretch_share(self) -> float:
        toks = self.token_list()
        forms = {s.word.casefold() for s in self.stretch}
        return sum(1 for t in toks if t in forms) / max(len(toks), 1)


class StoryFile(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    language: Language
    source: NonEmpty
    revision: NonEmpty
    license: NonEmpty
    review_status: Literal["unreviewed", "reviewed"]
    stories: list[LibraryStory] = Field(min_length=1)


def validate_story_file(f: StoryFile) -> list[str]:
    """Errors (empty = valid)."""
    errors: list[str] = []
    seen: set[str] = set()
    for s in f.stories:
        where = f"{f.language.value}/{s.slug}"
        if s.slug in seen:
            errors.append(f"{where}: duplicate slug")
        seen.add(s.slug)
        toks = set(s.token_list())
        for w in s.stretch:
            parts = [t.casefold() for t in tokens(w.word)]
            if not parts or any(p not in toks for p in parts):
                errors.append(f"{where}: stretch word {w.word!r} is not in the text")
        share = s.stretch_share()
        if share > MAX_STRETCH_SHARE:
            errors.append(f"{where}: stretch share {share:.0%} exceeds {MAX_STRETCH_SHARE:.0%}")
        if not any(line.speaker for line in s.lines) and len(s.lines) > 10:
            errors.append(f"{where}: narrative longer than 10 lines")
    return errors


def validate_parity(files: list[StoryFile]) -> list[str]:
    """Every language holds the same plots (slug and level)."""
    plots = {f.language: {(s.slug, s.level) for s in f.stories} for f in files}
    reference = next(iter(plots.values()), set())
    return [
        f"{lang.value}: plots differ from the other languages"
        for lang, p in plots.items()
        if p != reference
    ]


def validate_counts(f: StoryFile) -> list[str]:
    """The finished library holds STORIES_PER_LEVEL stories per level."""
    errors: list[str] = []
    for level in STORY_LEVELS:
        n = sum(1 for s in f.stories if s.level == level)
        if n != STORIES_PER_LEVEL:
            errors.append(
                f"{f.language.value}: {n} {level.value} stories, want {STORIES_PER_LEVEL}"
            )
    return errors
