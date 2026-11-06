"""What's new (Co je nového): release notes for the learner, filtered by the active language."""

from fastapi import APIRouter
from pydantic import BaseModel

from app.api.deps import DB, Auth
from app.domain import news
from app.domain.enums import Language
from app.schemas.profiles import ProfileSettings

router = APIRouter(prefix="/api/v1/news", tags=["news"])


class EntryOut(BaseModel):
    n: int
    date: str
    title: str
    blurb: str
    href: str | None
    new: bool


class NewsOut(BaseModel):
    latest: int
    unseen: int
    entries: list[EntryOut]  # newest first


def _out(language: Language, seen: int) -> NewsOut:
    return NewsOut(
        latest=news.LATEST,
        unseen=news.unseen(language, seen),
        entries=[
            EntryOut(n=e.n, date=e.date, title=e.title, blurb=e.blurb, href=e.href, new=e.n > seen)
            for e in news.for_language(language)
        ],
    )


@router.get("", response_model=NewsOut)
async def get_news(auth: Auth, language: Language | None = None) -> NewsOut:
    seen = ProfileSettings.from_stored(auth.acting.settings).news_seen
    return _out(language or Language(auth.acting.active_language), seen)


@router.post("/seen", response_model=NewsOut)
async def mark_seen(auth: Auth, db: DB) -> NewsOut:
    """Everything up to the newest entry counts as seen, for every language. Safe to repeat."""
    user = auth.acting
    stored = ProfileSettings.from_stored(user.settings)
    if stored.news_seen < news.LATEST:
        user.settings = {**stored.model_dump(mode="json"), "news_seen": news.LATEST}
        await db.commit()
    return _out(Language(user.active_language), news.LATEST)
