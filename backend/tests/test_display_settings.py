"""Reading comfort settings: stored per profile, validated, merged with the rest."""

import pytest

from app.api.deps import get_limiter
from app.main import app
from app.services.rate_limit import MemoryAttemptLimiter
from tests.helpers import csrf, setup_parent


@pytest.fixture(autouse=True)
def limiter():
    app.dependency_overrides[get_limiter] = lambda: MemoryAttemptLimiter()
    yield
    app.dependency_overrides.clear()


async def test_display_settings(db, client):
    me = await setup_parent(client)
    assert {
        k: me["acting"]["settings"][k] for k in ("text_size", "reading_spacing", "reduce_motion")
    } == {
        "text_size": "m",
        "reading_spacing": False,
        "reduce_motion": False,
    }
    r = await client.patch(
        "/api/v1/me/profile",
        json={"settings": {"text_size": "xl", "reading_spacing": True}},
        headers=csrf(me),
    )
    assert r.status_code == 200
    s = r.json()["settings"]
    assert s["text_size"] == "xl" and s["reading_spacing"] and not s["reduce_motion"]
    assert s["theme"] == "system"  # other settings untouched
    bad = await client.patch(
        "/api/v1/me/profile", json={"settings": {"text_size": "huge"}}, headers=csrf(me)
    )
    assert bad.status_code == 422


async def test_onboarded_flag(db, client):
    me = await setup_parent(client)
    assert me["acting"]["settings"]["onboarded"] is False
    r = await client.patch(
        "/api/v1/me/profile",
        json={"settings": {"onboarded": True, "daily_goal_minutes": 15}},
        headers=csrf(me),
    )
    s = r.json()["settings"]
    assert s["onboarded"] is True and s["daily_goal_minutes"] == 15
