"""Story library API: curated graded stories, gated by the content blacklist, never graded."""

from sqlalchemy import func, select

from app.db.session import get_session
from app.domain.enums import BlacklistCategory, BlacklistPatternType, Language
from app.models import ContentBlacklistEntry, LearningEvent
from app.services.library import story_file
from tests.helpers import setup_parent
from tests.test_learning import child_session


async def test_library_lists_the_language_file_with_provenance(db, client):
    await setup_parent(client)
    out = (await client.get("/api/v1/stories/library?language=de")).json()
    f = story_file(Language.DE)
    assert out["review_status"] == f.review_status == "unreviewed"
    assert out["source"] == f.source and out["license"] == f.license
    assert len(out["stories"]) == len(f.stories) == 90
    first = out["stories"][0]
    assert first["slug"] == f.stories[0].slug and first["level"] == "A1"
    assert first["title_cs"] and first["lines"] == len(f.stories[0].lines)
    assert first["kind"] in ("story", "dialogue") and first["stretch"] >= 1
    # Same plots in every language.
    en = (await client.get("/api/v1/stories/library?language=en")).json()
    assert [s["slug"] for s in en["stories"]] == [s["slug"] for s in out["stories"]]
    async for s in get_session():
        assert await s.scalar(select(func.count()).select_from(LearningEvent)) == 0


async def test_blacklisted_story_is_hidden_for_every_profile(db, client):
    f = story_file(Language.DE)
    title = f.stories[0].title  # e.g. "Der Regenschirm"
    async for s in get_session():
        s.add(
            ContentBlacklistEntry(
                language=Language.DE,
                pattern_type=BlacklistPatternType.KEYWORD,
                pattern=title,
                category=BlacklistCategory.OTHER,
            )
        )
        await s.commit()
    await child_session(client)
    out = (await client.get("/api/v1/stories/library?language=de")).json()
    slugs = [s["slug"] for s in out["stories"]]
    assert f.stories[0].slug not in slugs and len(slugs) == 89
    # The French file is not matched by a German-only pattern.
    fr = (await client.get("/api/v1/stories/library?language=fr")).json()
    assert len(fr["stories"]) == 90


async def test_library_needs_a_session(db, client):
    assert (await client.get("/api/v1/stories/library?language=de")).status_code == 401


async def test_reading_a_story_returns_lines_with_czech_and_hides_gated_ones(db, client):
    await setup_parent(client)
    f = story_file(Language.DE)
    first = f.stories[0]
    out = (await client.get(f"/api/v1/stories/library/{first.slug}?language=de")).json()
    assert out["title"] == first.title and out["level"] == "A1"
    assert [ln["text"] for ln in out["lines"]] == [ln.text for ln in first.lines]
    assert all(ln["cs"] for ln in out["lines"]) and out["review_status"] == "unreviewed"
    # Unknown, malformed, or gated slugs are all plain 404s/422s, never another language's text.
    assert (await client.get("/api/v1/stories/library/zz-nothing?language=de")).status_code == 404
    assert (await client.get("/api/v1/stories/library/Bad_Slug?language=de")).status_code == 422
    async for s in get_session():
        s.add(
            ContentBlacklistEntry(
                language=Language.DE,
                pattern_type=BlacklistPatternType.KEYWORD,
                pattern=first.title,
                category=BlacklistCategory.OTHER,
            )
        )
        await s.commit()
    r = await client.get(f"/api/v1/stories/library/{first.slug}?language=de")
    assert r.status_code == 404
