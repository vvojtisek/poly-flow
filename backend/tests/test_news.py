"""What's new: numbering, language filter, unseen count and marking seen."""

import pytest

from app.api.deps import get_limiter
from app.domain import news
from app.domain.enums import Language
from app.main import app
from app.services.rate_limit import MemoryAttemptLimiter
from tests.helpers import csrf, login, make_child, setup_parent


@pytest.fixture(autouse=True)
def limiter():
    # login() goes through the attempt limiter; keep it in memory, not in a loop-bound client.
    app.dependency_overrides[get_limiter] = lambda: MemoryAttemptLimiter()
    yield
    app.dependency_overrides.clear()


def test_numbers_grow_by_one_and_never_repeat():
    assert [e.n for e in news.ENTRIES] == list(range(1, len(news.ENTRIES) + 1))
    assert news.LATEST == news.ENTRIES[-1].n


def test_entries_are_czech_and_point_to_pages():
    for e in news.ENTRIES:
        assert e.title and e.blurb and len(e.blurb) <= 200
        assert e.href is None or e.href.startswith("/")


def test_language_filter():
    de = {e.n for e in news.for_language(Language.DE)}
    en = {e.n for e in news.for_language(Language.EN)}
    case_lab = next(e.n for e in news.ENTRIES if e.href == "/grammar/cases")
    verbs = next(e.n for e in news.ENTRIES if e.href == "/grammar/verbs")
    assert case_lab in de and case_lab not in en
    assert verbs in de and verbs not in en
    assert news.for_language(Language.DE)[0].n == news.LATEST  # newest first


def test_unseen_counts_only_newer_entries_of_the_language():
    assert news.unseen(Language.DE, 0) == len(news.for_language(Language.DE))
    assert news.unseen(Language.DE, news.LATEST) == 0
    assert news.unseen(Language.EN, 0) < news.unseen(Language.DE, 0)


async def test_news_api(db, client):
    me = await setup_parent(client)
    out = (await client.get("/api/v1/news")).json()
    lang = me["acting"]["active_language"]
    assert out["latest"] == news.LATEST
    assert out["unseen"] == news.unseen(Language(lang), 0) and out["unseen"] > 0
    assert all(e["new"] for e in out["entries"])

    en = (await client.get("/api/v1/news?language=en")).json()
    assert all(e["href"] != "/grammar/cases" for e in en["entries"])

    for _ in range(2):  # repeating is harmless
        seen = await client.post("/api/v1/news/seen", headers=csrf(me))
        assert seen.status_code == 200 and seen.json()["unseen"] == 0
    after = (await client.get("/api/v1/news")).json()
    assert after["unseen"] == 0 and not any(e["new"] for e in after["entries"])
    settings = (await client.get("/api/v1/me/profile")).json()["settings"]
    assert settings["news_seen"] == news.LATEST and settings["onboarded"] is False  # untouched


async def test_news_seen_is_per_profile_and_needs_csrf(db, client):
    parent = await setup_parent(client)
    assert (await client.post("/api/v1/news/seen")).status_code == 403
    await make_child(client, parent)
    await client.post("/api/v1/news/seen", headers=csrf(parent))
    assert (await client.get("/api/v1/news")).json()["unseen"] == 0
    await login(client, "eva", "4321")
    assert (await client.get("/api/v1/news")).json()["unseen"] > 0  # the child has not seen it
