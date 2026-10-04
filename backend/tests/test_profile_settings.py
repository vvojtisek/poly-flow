"""A profile's own preferences: theme, interests, speech voice and speed."""

import pytest
from sqlalchemy import update

from app.api.deps import get_limiter
from app.db.session import get_session
from app.main import app
from app.models import User
from app.schemas.profiles import ProfileSettings
from app.services.rate_limit import MemoryAttemptLimiter
from tests.helpers import csrf, make_child, setup_parent

URL = "/api/v1/me/profile"


@pytest.fixture(autouse=True)
def limiter():
    app.dependency_overrides[get_limiter] = MemoryAttemptLimiter
    yield
    app.dependency_overrides.pop(get_limiter, None)


async def patch(client, me, settings: dict):
    return await client.patch(URL, json={"settings": settings}, headers=csrf(me))


async def test_defaults_for_a_new_profile(db, client):
    me = await setup_parent(client)
    s = me["acting"]["settings"]
    assert s["theme"] == "system" and s["interests"] == [] and s["voices"] == {}
    assert s["audio_rate"] == 1.0


async def test_settings_are_saved_and_a_partial_update_keeps_the_rest(db, client):
    me = await setup_parent(client)
    r = await patch(
        client,
        me,
        {
            "theme": "dark",
            "interests": ["travel", " Formule  1 ", "formule 1", "Vaření"],
            "voices": {"fr": "fr_FR-siwis-medium"},
            "audio_rate": 0.8,
        },
    )
    assert r.status_code == 200, r.text
    s = r.json()["settings"]
    assert s["theme"] == "dark"
    assert s["interests"] == ["travel", "formule 1", "vaření"]
    assert s["voices"] == {"fr": "fr_FR-siwis-medium"} and s["audio_rate"] == 0.8

    r = await patch(client, me, {"theme": "light"})
    s = r.json()["settings"]
    assert s["theme"] == "light" and s["interests"] == ["travel", "formule 1", "vaření"]
    assert s["voices"] == {"fr": "fr_FR-siwis-medium"} and s["audio_rate"] == 0.8
    assert (await client.get(URL)).json()["settings"] == s


@pytest.mark.parametrize(
    "settings",
    [
        {"theme": "blue"},
        {"interests": ["x" * 41]},
        {"interests": [f"t{i}" for i in range(21)]},
        {"interests": ["<script>"]},
        {"voices": {"de": "fr_FR-siwis-medium"}},  # a French voice for German
        {"voices": {"de": "de_DE-unknown"}},
        {"voices": {"es": "de_DE-thorsten-medium"}},
        {"audio_rate": 3},
        {"unknown": True},
    ],
)
async def test_invalid_settings_are_rejected(db, client, settings):
    me = await setup_parent(client)
    assert (await patch(client, me, settings)).status_code == 422


async def test_a_child_chooses_its_own_settings_and_the_admin_cannot(db, client):
    parent = await setup_parent(client)
    eva = await make_child(client, parent)
    r = await client.patch(
        f"/api/v1/profiles/{eva['id']}", json={"settings": {"theme": "dark"}}, headers=csrf(parent)
    )
    assert r.status_code == 422
    client.cookies.clear()
    child = (
        await client.post("/api/v1/auth/login", json={"username": "eva", "secret": "4321"})
    ).json()
    r = await patch(client, child, {"theme": "dark", "interests": ["animals"]})
    assert r.status_code == 200 and r.json()["is_child"] is True


async def test_a_removed_voice_does_not_break_the_profile(db, client):
    me = await setup_parent(client)
    async for session in get_session():
        await session.execute(
            update(User).values(
                settings={"theme": "dark", "voices": {"de": "de_DE-gone-low", "it": 7}}
            )
        )
        await session.commit()
    r = await client.get(URL)
    assert r.status_code == 200
    assert r.json()["settings"]["voices"] == {} and r.json()["settings"]["theme"] == "dark"
    assert (await patch(client, me, {"audio_rate": 1.2})).status_code == 200


def test_stored_settings_from_before_this_change_still_read():
    s = ProfileSettings.from_stored({"daily_goal_minutes": 15, "audio_rate": 1.0})
    assert s.theme == "system" and s.interests == [] and s.voices == {}
