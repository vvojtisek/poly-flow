from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api import (
    auth,
    declension,
    diagnostic,
    dictation,
    genders,
    grammar,
    health,
    insights,
    learning,
    lexicon,
    lookup,
    numbers,
    profiles,
    progression,
    ranks,
    review,
    roleplay,
    stories,
    today,
    tutor,
    verbs,
    voices,
    word_order,
    words,
)
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.middleware import RequestLoggingMiddleware
from app.db.session import dispose_engine


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield
    await dispose_engine()


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(title="PolyFlow API", version=__version__, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestLoggingMiddleware)  # outermost: sees every request
    app.include_router(health.router)
    app.include_router(progression.router)
    app.include_router(auth.router)
    app.include_router(profiles.router)
    app.include_router(voices.router)
    app.include_router(learning.router)
    app.include_router(diagnostic.router)
    app.include_router(ranks.router)
    app.include_router(insights.router)
    app.include_router(words.router)
    app.include_router(today.router)
    app.include_router(declension.router)
    app.include_router(genders.router)
    app.include_router(review.router)
    app.include_router(roleplay.router)
    app.include_router(verbs.router)
    app.include_router(lookup.router)
    app.include_router(numbers.router)
    app.include_router(word_order.router)
    app.include_router(dictation.router)
    app.include_router(grammar.router)
    app.include_router(tutor.router)
    app.include_router(stories.router)
    app.include_router(lexicon.router)
    return app


app = create_app()
