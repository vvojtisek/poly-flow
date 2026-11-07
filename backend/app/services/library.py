"""Story library: the curated graded stories in `data/stories/` (A1-B2, same plots per language).

The files are drafts without native-speaker review, so every story is served with the file's
review status and its source/licence. Before a story is listed or read it must pass the active
content blacklist (the same gate generated readings pass); a story that fails is hidden for every
profile, children included. Reading is ungraded practice: nothing here records evidence.
"""

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import Language
from app.domain.story_library import LibraryStory, StoryFile, validate_story_file
from app.models import User
from app.services.learning import LearningError
from app.services.safety import blacklist_matcher

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "stories"


@lru_cache
def story_file(language: Language) -> StoryFile | None:
    """The language's library, parsed and validated once per process (None = no file)."""
    path = DATA_DIR / f"{Language(language).value}.stories.json"
    if not path.exists():
        return None
    f = StoryFile.model_validate(json.loads(path.read_text(encoding="utf-8")))
    errors = validate_story_file(f)
    if errors:  # a broken file is a deployment error, not something to half-serve
        raise ValueError(f"invalid story library {path.name}: {errors[:3]}")
    return f


def full_text(s: LibraryStory) -> str:
    """Everything a reader sees, for the safety gate."""
    return " ".join(
        [s.title, s.title_cs]
        + [f"{ln.speaker or ''} {ln.text} {ln.cs}" for ln in s.lines]
        + [f"{w.word} {w.cs}" for w in s.stretch]
        + [q.question + " " + " ".join(q.options) for q in s.questions]
    )


@dataclass
class Library:
    file: StoryFile
    stories: list[LibraryStory]  # file order (level, then plot number), safe ones only


async def library(db: AsyncSession, user: User, language: Language) -> Library | None:
    f = story_file(language)
    if f is None:
        return None
    hits = await blacklist_matcher(db, [language])
    return Library(f, [s for s in f.stories if not hits(full_text(s))])


async def story(db: AsyncSession, user: User, language: Language, slug: str) -> Library:
    lib = await library(db, user, language)
    found = next((s for s in lib.stories if s.slug == slug), None) if lib else None
    if lib is None or found is None:
        raise LearningError("story_not_found", 404)
    return Library(lib.file, [found])
