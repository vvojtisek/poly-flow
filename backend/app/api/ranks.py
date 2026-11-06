"""Personal mastery ranks and achievements (single player, per language)."""

from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.api.deps import DB, Auth
from app.api.learning import Now
from app.domain.enums import Language
from app.services import ranks as svc

router = APIRouter(prefix="/api/v1/ranks", tags=["learning"])

Tier = Literal["bronze", "silver", "gold", "platinum", "diamond"]


class RequirementOut(BaseModel):
    key: Literal["known_words", "grammar_known", "badge", "recoveries"]
    target: int
    current: int
    level: str | None
    met: bool


class NextOut(BaseModel):
    rank: int
    tier: Tier
    requirements: list[RequirementOut]


class RankOut(BaseModel):
    rank: int
    tier: Tier
    reached_at: datetime | None
    requirements: list[RequirementOut]


class AchievementOut(BaseModel):
    key: str
    group: str
    reached_at: datetime | None


class StatsOut(BaseModel):
    known_words: int
    passive_words: int
    grammar_known: int
    grammar_total: int
    recoveries: int
    checks_answered: int
    badges: list[str]


class RanksOut(BaseModel):
    language: Language
    path: Literal["hockey", "royal", "off"]
    rank: int
    max_rank: int
    tier: Tier
    next: NextOut | None
    ranks: list[RankOut]
    achievements: list[AchievementOut]
    unseen_rank: int | None
    unseen_achievements: list[str]
    stats: StatsOut


class SeenIn(BaseModel):
    language: Language | None = None


@router.get("", response_model=RanksOut)
async def get_ranks(
    auth: Auth, db: DB, now: Now, language: Annotated[Language | None, Query()] = None
) -> RanksOut:
    out = await svc.overview(db, auth.acting, language or auth.acting.active_language, now)
    await db.commit()  # newly reached awards are recorded once
    return RanksOut(**out)


@router.post("/seen", status_code=204)
async def seen(body: SeenIn, auth: Auth, db: DB, now: Now) -> None:
    await svc.mark_seen(db, auth.acting, body.language or auth.acting.active_language, now)
    await db.commit()
