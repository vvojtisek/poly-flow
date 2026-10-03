from fastapi import APIRouter
from pydantic import BaseModel

from app.domain.enums import CefrLevel
from app.domain.progression import CURRICULUM_END, MILESTONES

router = APIRouter(prefix="/api/v1/progression", tags=["progression"])


class MilestoneOut(BaseModel):
    rank: int
    key: str
    cefr: CefrLevel | None
    voluntary: bool
    passive_focus: bool


class ProgressionOut(BaseModel):
    curriculum_end: int
    milestones: list[MilestoneOut]


@router.get("/milestones", response_model=ProgressionOut)
async def milestones() -> ProgressionOut:
    return ProgressionOut(
        curriculum_end=CURRICULUM_END,
        milestones=[
            MilestoneOut(
                rank=m.rank,
                key=m.key,
                cefr=m.cefr,
                voluntary=m.voluntary,
                passive_focus=m.passive_focus,
            )
            for m in MILESTONES
        ],
    )
