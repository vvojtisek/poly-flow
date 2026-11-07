"""Content screening of generated text against the active blacklist.

A pattern list is not a safety boundary on its own (AGENTS.md): callers use this as one gate
among others, and child profiles fall back to reviewed content whenever a check fails.
"""

import re
from collections.abc import Callable

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import BlacklistPatternType, Language
from app.models import ContentBlacklistEntry


async def blacklist_matcher(
    db: AsyncSession, languages: list[Language]
) -> Callable[[str], list[str]]:
    """Loads the active patterns once; the returned function lists the categories `text` hits."""
    rows = (
        await db.execute(
            select(ContentBlacklistEntry).where(
                ContentBlacklistEntry.is_active.is_(True),
                or_(
                    ContentBlacklistEntry.language.is_(None),
                    ContentBlacklistEntry.language.in_(languages),
                ),
            )
        )
    ).scalars()
    compiled: list[tuple[re.Pattern[str], str]] = []
    for e in rows:
        if e.pattern_type == BlacklistPatternType.KEYWORD:
            rx = re.compile(rf"(?<!\w){re.escape(e.pattern)}(?!\w)", re.IGNORECASE)
        else:
            try:
                rx = re.compile(e.pattern, re.IGNORECASE)
            except re.error:
                continue
        compiled.append((rx, e.category.value))

    def hits(text: str) -> list[str]:
        return sorted({category for rx, category in compiled if rx.search(text)})

    return hits


async def blacklist_hits(db: AsyncSession, text: str, languages: list[Language]) -> list[str]:
    """Categories of active blacklist patterns that match `text` (empty list = clean)."""
    return (await blacklist_matcher(db, languages))(text)


_PROMPT_LEAK = re.compile(r"(?i)\b(system prompt|ignore (all|previous) instructions|as an ai)\b")
_CZECH_CHARS = re.compile(r"[ěščřžýáíéůú]", re.IGNORECASE)


def looks_like_czech_explanation(text: str, *, max_chars: int) -> bool:
    """Cheap shape check: bounded, contains Czech diacritics, no prompt-injection echo."""
    if not text or len(text) > max_chars:
        return False
    if _PROMPT_LEAK.search(text):
        return False
    return len(_CZECH_CHARS.findall(text)) >= 3
