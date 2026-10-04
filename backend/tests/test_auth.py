"""Profiles, sessions and authorization (plan P1)."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import update

from app.api.deps import get_limiter
from app.main import app
from app.services.rate_limit import MemoryAttemptLimiter

PARENT = {"username": "mama", "display_name": "Máma", "password": "correct horse 1"}


@pytest.fixture(autouse=True)
def limiter():
    lim = MemoryAttemptLimiter()
    app.dependency_overrides[get_limiter] = lambda: lim
    yield lim
    app.dependency_overrides.pop(get_limiter, None)


def csrf(me: dict) -> dict:
    return {"X-CSRF-Token": me["csrf_token"]}


async def setup_parent(client) -> dict:
    r = await client.post("/api/v1/setup", json=PARENT)
    assert r.status_code == 201, r.text
    return r.json()


async def create(client, me, **body) -> dict:
    r = await client.post("/api/v1/profiles", json=body, headers=csrf(me))
    assert r.status_code == 201, r.text
    return r.json()


async def test_setup_only_once(db, client):
    assert (await client.get("/api/v1/setup")).json() == {"needs_setup": True}
    me = await setup_parent(client)
    assert me["can_manage"] and me["principal"]["role"] == "admin"
    assert (await client.get("/api/v1/setup")).json() == {"needs_setup": False}
    r = await client.post("/api/v1/setup", json={**PARENT, "username": "attacker"})
    assert r.status_code == 409


async def test_cookie_is_httponly_and_lax(db, client):
    r = await client.post("/api/v1/setup", json=PARENT)
    cookie = r.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=lax" in cookie


async def test_login_logout_and_unauthenticated(db, client):
    await setup_parent(client)
    client.cookies.clear()
    assert (await client.get("/api/v1/auth/me")).status_code == 401
    bad = await client.post("/api/v1/auth/login", json={"username": "mama", "secret": "nope"})
    assert bad.status_code == 401
    r = await client.post(
        "/api/v1/auth/login", json={"username": "MAMA", "secret": PARENT["password"]}
    )
    assert r.status_code == 200
    me = r.json()
    assert (await client.get("/api/v1/auth/me")).status_code == 200
    assert (await client.post("/api/v1/auth/logout", headers=csrf(me))).status_code == 204
    assert (await client.get("/api/v1/auth/me")).status_code == 401


async def test_unknown_user_and_wrong_password_look_the_same(db, client):
    await setup_parent(client)
    a = await client.post("/api/v1/auth/login", json={"username": "ghost", "secret": "x" * 9})
    b = await client.post("/api/v1/auth/login", json={"username": "mama", "secret": "x" * 9})
    assert a.status_code == b.status_code == 401
    assert a.json() == b.json()


async def test_login_rate_limited(db, client):
    await setup_parent(client)
    for _ in range(5):
        r = await client.post("/api/v1/auth/login", json={"username": "mama", "secret": "wrong"})
        assert r.status_code == 401
    r = await client.post(
        "/api/v1/auth/login", json={"username": "mama", "secret": PARENT["password"]}
    )
    assert r.status_code == 429  # blocked even with the right password


async def test_csrf_required_for_writes(db, client):
    me = await setup_parent(client)
    body = {"username": "eva", "display_name": "Eva", "kind": "child", "pin": "4321"}
    assert (await client.post("/api/v1/profiles", json=body)).status_code == 403
    r = await client.post("/api/v1/profiles", json=body, headers={"X-CSRF-Token": "forged"})
    assert r.status_code == 403
    assert (await client.post("/api/v1/profiles", json=body, headers=csrf(me))).status_code == 201


async def test_profile_rules(db, client):
    me = await setup_parent(client)
    h = csrf(me)
    for body in (
        {"username": "tata", "display_name": "Táta", "kind": "adult"},
        {"username": "eva", "display_name": "Eva", "kind": "child"},
        {
            "username": "eva",
            "display_name": "Eva",
            "kind": "child",
            "pin": "4321",
            "password": "x" * 8,
        },
    ):
        r = await client.post("/api/v1/profiles", json=body, headers=h)
        assert r.status_code == 422, body  # exactly one of password / PIN
    # The learner picks their own language; the admin cannot assign one.
    r = await client.post(
        "/api/v1/profiles",
        json={
            "username": "eva",
            "display_name": "Eva",
            "kind": "child",
            "pin": "4321",
            "active_language": "fr",
        },
        headers=h,
    )
    assert r.status_code == 422
    await create(client, me, username="eva", display_name="Eva", kind="child", pin="4321")
    r = await client.post(
        "/api/v1/profiles",
        json={"username": "eva", "display_name": "Eva 2", "kind": "child", "pin": "4321"},
        headers=h,
    )
    assert r.status_code == 409


async def test_child_with_password_and_adult_with_pin_sign_in(db, client):
    """The content filter and the kind of sign-in are independent."""
    me = await setup_parent(client)
    await create(
        client, me, username="eva", display_name="Eva", kind="child", password="eva-heslo-1"
    )
    await create(client, me, username="deda", display_name="Děda", kind="adult", pin="2468")
    client.cookies.clear()
    r = await client.post("/api/v1/auth/login", json={"username": "eva", "secret": "eva-heslo-1"})
    assert r.status_code == 200 and r.json()["acting"]["is_child"] is True
    client.cookies.clear()
    r = await client.post("/api/v1/auth/login", json={"username": "deda", "secret": "2468"})
    assert r.status_code == 200 and r.json()["acting"]["is_child"] is False


async def test_child_with_pin_signs_in_but_cannot_manage(db, client):
    me = await setup_parent(client)
    await create(client, me, username="eva", display_name="Eva", kind="child", pin="4321")
    client.cookies.clear()
    r = await client.post("/api/v1/auth/login", json={"username": "eva", "secret": "4321"})
    assert r.status_code == 200
    child = r.json()
    assert child["can_manage"] is False and child["acting"]["is_child"] is True
    assert (await client.get("/api/v1/profiles")).status_code == 403
    r = await client.post(
        "/api/v1/profiles",
        json={"username": "x1y", "display_name": "X", "kind": "adult", "password": "p" * 10},
        headers=csrf(child),
    )
    assert r.status_code == 403


async def test_child_cannot_change_safety_fields(db, client):
    me = await setup_parent(client)
    await create(client, me, username="eva", display_name="Eva", kind="child", pin="4321")
    client.cookies.clear()
    child = (
        await client.post("/api/v1/auth/login", json={"username": "eva", "secret": "4321"})
    ).json()
    for forbidden in ({"is_child": False}, {"role": "admin"}, {"pin": "0000"}):
        r = await client.patch("/api/v1/me/profile", json=forbidden, headers=csrf(child))
        assert r.status_code == 422, forbidden
    ok = await client.patch(
        "/api/v1/me/profile",
        json={"active_language": "it", "settings": {"daily_goal_minutes": 15}},
        headers=csrf(child),
    )
    assert ok.status_code == 200
    assert ok.json()["is_child"] is True and ok.json()["active_language"] == "it"


async def test_parent_hands_device_to_child_and_back(db, client):
    me = await setup_parent(client)
    eva = await create(client, me, username="eva", display_name="Eva", kind="child", pin="4321")
    r = await client.post("/api/v1/auth/switch", json={"profile_id": eva["id"]}, headers=csrf(me))
    assert r.status_code == 200
    switched = r.json()
    assert switched["acting"]["id"] == eva["id"] and switched["can_manage"] is False
    assert (await client.get("/api/v1/me/profile")).json()["username"] == "eva"
    assert (await client.get("/api/v1/profiles")).status_code == 403
    # The child holding the device cannot get back into the parent's account without the password.
    r = await client.post("/api/v1/auth/return", json={"password": "guess"}, headers=csrf(me))
    assert r.status_code == 401
    r = await client.post(
        "/api/v1/auth/return", json={"password": PARENT["password"]}, headers=csrf(me)
    )
    assert r.status_code == 200 and r.json()["can_manage"] is True
    assert (await client.get("/api/v1/profiles")).status_code == 200


async def test_switch_only_to_child_profiles(db, client):
    me = await setup_parent(client)
    tata = await create(
        client, me, username="tata", display_name="Táta", kind="adult", password="tata-heslo-1"
    )
    r = await client.post("/api/v1/auth/switch", json={"profile_id": tata["id"]}, headers=csrf(me))
    assert r.status_code == 404


async def test_adult_learner_sees_only_own_profile(db, client):
    me = await setup_parent(client)
    tata = await create(
        client, me, username="tata", display_name="Táta", kind="adult", password="tata-heslo-1"
    )
    eva = await create(client, me, username="eva", display_name="Eva", kind="child", pin="4321")
    client.cookies.clear()
    t = (
        await client.post("/api/v1/auth/login", json={"username": "tata", "secret": "tata-heslo-1"})
    ).json()
    assert t["can_manage"] is False
    assert (await client.get("/api/v1/profiles")).status_code == 403
    r = await client.patch(
        f"/api/v1/profiles/{eva['id']}", json={"display_name": "hacked"}, headers=csrf(t)
    )
    assert r.status_code == 403
    r = await client.post("/api/v1/auth/switch", json={"profile_id": eva["id"]}, headers=csrf(t))
    assert r.status_code == 403
    assert (await client.get("/api/v1/me/profile")).json()["id"] == tata["id"]


async def test_deactivation_and_pin_change_revoke_sessions(db, client):
    me = await setup_parent(client)
    eva = await create(client, me, username="eva", display_name="Eva", kind="child", pin="4321")
    parent_cookie = client.cookies.get("pf_session")
    client.cookies.clear()
    await client.post("/api/v1/auth/login", json={"username": "eva", "secret": "4321"})
    child_cookie = client.cookies.get("pf_session")

    client.cookies.set("pf_session", parent_cookie)
    r = await client.patch(f"/api/v1/profiles/{eva['id']}", json={"pin": "9999"}, headers=csrf(me))
    assert r.status_code == 200
    client.cookies.set("pf_session", child_cookie)
    assert (await client.get("/api/v1/auth/me")).status_code == 401

    client.cookies.set("pf_session", parent_cookie)
    await client.patch(f"/api/v1/profiles/{eva['id']}", json={"is_active": False}, headers=csrf(me))
    client.cookies.clear()
    r = await client.post("/api/v1/auth/login", json={"username": "eva", "secret": "9999"})
    assert r.status_code == 401


async def test_admin_manages_access_not_learning_choices(db, client):
    me = await setup_parent(client)
    eva = await create(client, me, username="eva", display_name="Eva", kind="child", pin="4321")
    url = f"/api/v1/profiles/{eva['id']}"
    for forbidden in (
        {"active_language": "fr"},
        {"settings": {"daily_goal_minutes": 30}},
        {"timezone": "Europe/Berlin"},
        {"role": "admin"},
    ):
        r = await client.patch(url, json=forbidden, headers=csrf(me))
        assert r.status_code == 422, forbidden
    # Switching to a password replaces the PIN; the filter can be turned off as the kid grows up.
    r = await client.patch(
        url, json={"password": "eva-heslo-1", "is_child": False}, headers=csrf(me)
    )
    assert r.status_code == 200
    assert r.json()["is_child"] is False and r.json()["has_pin"] is False
    client.cookies.clear()
    r = await client.post("/api/v1/auth/login", json={"username": "eva", "secret": "4321"})
    assert r.status_code == 401
    r = await client.post("/api/v1/auth/login", json={"username": "eva", "secret": "eva-heslo-1"})
    assert r.status_code == 200


async def test_admin_keeps_password_and_no_filter(db, client):
    me = await setup_parent(client)
    url = f"/api/v1/profiles/{me['principal']['id']}"
    assert (await client.patch(url, json={"pin": "1234"}, headers=csrf(me))).status_code == 422
    assert (await client.patch(url, json={"is_child": True}, headers=csrf(me))).status_code == 422


async def test_expired_session_rejected(db, client):
    await setup_parent(client)
    from app.db.session import get_engine
    from app.models import AuthSession

    async with get_engine().begin() as conn:
        await conn.execute(
            update(AuthSession).values(expires_at=datetime.now(UTC) - timedelta(seconds=1))
        )
    assert (await client.get("/api/v1/auth/me")).status_code == 401


async def test_admin_cannot_be_deleted_or_self_deactivated(db, client):
    me = await setup_parent(client)
    pid = me["principal"]["id"]
    assert (await client.delete(f"/api/v1/profiles/{pid}", headers=csrf(me))).status_code == 422
    r = await client.patch(f"/api/v1/profiles/{pid}", json={"is_active": False}, headers=csrf(me))
    assert r.status_code == 422


async def test_invalid_timezone_rejected(db, client):
    me = await setup_parent(client)
    r = await client.patch("/api/v1/me/profile", json={"timezone": "Mars/Base"}, headers=csrf(me))
    assert r.status_code == 422
