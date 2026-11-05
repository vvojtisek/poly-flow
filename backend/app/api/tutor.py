import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, StringConstraints

from app.api.deps import DB, Auth
from app.services import tutor as svc
from app.services.learning import LearningError
from app.services.llm import Llm, get_llm

router = APIRouter(prefix="/api/v1/tutor", tags=["tutor"])
LlmDep = Annotated[Llm, Depends(get_llm)]


class ExplainIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["word", "grammar"]
    id: uuid.UUID  # a word task id or a grammar session item id
    question: Annotated[str, StringConstraints(strip_whitespace=True, max_length=300)] | None = None


class ExplainOut(BaseModel):
    source: Literal["curriculum", "model"]
    text: str
    model: str | None
    can_ask: bool  # a follow-up question can be answered (a model is available to this profile)


class StatusOut(BaseModel):
    model_available: bool
    model: str | None


@router.get("/status", response_model=StatusOut)
async def status(auth: Auth, llm: LlmDep) -> StatusOut:
    ok = svc.model_allowed(auth.acting, llm)
    return StatusOut(model_available=ok, model=llm.model if ok else None)


@router.post("/explain", response_model=ExplainOut)
async def explain(body: ExplainIn, auth: Auth, db: DB, llm: LlmDep) -> ExplainOut:
    try:
        e = await svc.explain(
            db, auth.acting, llm, kind=body.kind, ref_id=body.id, question=body.question
        )
    except LearningError as exc:
        await db.rollback()
        raise HTTPException(exc.status, exc.code) from exc
    await db.commit()
    return ExplainOut(source=e.source, text=e.text, model=e.model, can_ask=e.model_available)
