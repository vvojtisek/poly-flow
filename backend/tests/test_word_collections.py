"""Learner-owned word collections preserve dictionary visibility and profile isolation."""

import csv
import io
import uuid

import pytest
from sqlalchemy import select

from app.api.deps import get_limiter
from app.api.learning import get_now
from app.db.session import get_session
from app.main import app
from app.models import LexiconItem, User
from app.services.rate_limit import MemoryAttemptLimiter
from tests.helpers import Clock, csrf, login, make_child, setup_parent
from tests.test_words import seed


@pytest.fixture(autouse=True)
def clock():
    c = Clock()
    app.dependency_overrides[get_now] = lambda: c.now
    app.dependency_overrides[get_limiter] = lambda: MemoryAttemptLimiter()
    yield c
    app.dependency_overrides.clear()


async def test_collection_crud_is_private_and_only_accepts_encountered_words(db, client, clock):
    me = await setup_parent(client)
    ids = await seed(uuid.UUID(me["acting"]["id"]), clock)
    async for session in get_session():
        word = await session.scalar(select(LexiconItem).where(LexiconItem.id == ids["Haus"]))
        word.example_sentence = "Ich kaufe ein Haus."
        await session.commit()
        break
    created = await client.post(
        "/api/v1/words/collections",
        json={"language": "de", "name": "  Na   cestě  "},
        headers=csrf(me),
    )
    assert created.status_code == 201
    collection_id = created.json()["id"]
    assert created.json()["name"] == "Na cestě"

    french = await client.post(
        "/api/v1/words/collections",
        json={"language": "fr", "name": "Mots français"},
        headers=csrf(me),
    )
    assert french.status_code == 201
    assert (
        await client.post(
            f"/api/v1/words/collections/{french.json()['id']}/items",
            json={"item_id": str(ids["Haus"])},
            headers=csrf(me),
        )
    ).status_code == 404

    assert (
        await client.post(
            f"/api/v1/words/collections/{collection_id}/items",
            json={"item_id": str(ids["Haus"])},
            headers=csrf(me),
        )
    ).status_code == 204
    # Retrying an add is safe and does not duplicate the item.
    assert (
        await client.post(
            f"/api/v1/words/collections/{collection_id}/items",
            json={"item_id": str(ids["Haus"])},
            headers=csrf(me),
        )
    ).status_code == 204
    assert (
        await client.post(
            f"/api/v1/words/collections/{collection_id}/items",
            json={"item_id": str(ids["neu"])},
            headers=csrf(me),
        )
    ).status_code == 404

    detail = (await client.get(f"/api/v1/words/collections/{collection_id}")).json()
    assert detail["name"] == "Na cestě"
    assert [word["lemma"] for word in detail["items"]] == ["Haus"]
    assert detail["items"][0]["example"] == "Ich kaufe ein Haus."
    assert (await client.get("/api/v1/words/collections?language=de")).json()[0]["count"] == 1
    assert (
        await client.delete(
            f"/api/v1/words/collections/{collection_id}/items/{ids['Haus']}", headers=csrf(me)
        )
    ).status_code == 204
    assert (await client.get(f"/api/v1/words/collections/{collection_id}")).json()["items"] == []


async def test_collections_do_not_cross_profiles_or_child_content_filter(db, client, clock):
    parent = await setup_parent(client)
    child = await make_child(client, parent)
    ids = await seed(uuid.UUID(child["id"]), clock)
    child_me = await login(client, "eva", "4321")
    created = await client.post(
        "/api/v1/words/collections",
        json={"language": "de", "name": "Bezpečná slova"},
        headers=csrf(child_me),
    )
    assert created.status_code == 201
    collection_id = created.json()["id"]
    assert (
        await client.post(
            f"/api/v1/words/collections/{collection_id}/items",
            json={"item_id": str(ids["Mord"])},
            headers=csrf(child_me),
        )
    ).status_code == 404
    assert (await client.get(f"/api/v1/words/collections/{collection_id}")).json()["items"] == []
    parent_session = await login(client, "mama", "correct horse 1")
    assert (await client.get(f"/api/v1/words/collections/{collection_id}")).status_code == 404
    assert parent_session["acting"]["username"] == "mama"


async def test_duplicate_collection_name_is_conflict(db, client):
    me = await setup_parent(client)
    payload = {"language": "de", "name": "Cestování"}
    assert (
        await client.post("/api/v1/words/collections", json=payload, headers=csrf(me))
    ).status_code == 201
    assert (
        await client.post("/api/v1/words/collections", json=payload, headers=csrf(me))
    ).status_code == 409


async def test_collection_count_and_contents_reapply_child_filter(db, client, clock):
    me = await setup_parent(client)
    ids = await seed(uuid.UUID(me["acting"]["id"]), clock)
    created = await client.post(
        "/api/v1/words/collections",
        json={"language": "de", "name": "Později skrytá slova"},
        headers=csrf(me),
    )
    collection_id = created.json()["id"]
    assert (
        await client.post(
            f"/api/v1/words/collections/{collection_id}/items",
            json={"item_id": str(ids["Mord"])},
            headers=csrf(me),
        )
    ).status_code == 204

    async for session in get_session():
        user = await session.scalar(select(User).where(User.id == uuid.UUID(me["acting"]["id"])))
        user.is_child = True
        await session.commit()
        break

    listed = await client.get("/api/v1/words/collections?language=de")
    assert listed.status_code == 200
    assert listed.json()[0]["count"] == 0
    detail = await client.get(f"/api/v1/words/collections/{collection_id}")
    assert detail.json()["items"] == []


async def test_collection_export_contains_only_visible_selected_words(db, client, clock):
    me = await setup_parent(client)
    ids = await seed(uuid.UUID(me["acting"]["id"]), clock)
    collection = await client.post(
        "/api/v1/words/collections",
        json={"language": "de", "name": "Výlet"},
        headers=csrf(me),
    )
    collection_id = collection.json()["id"]
    for lemma in ("Haus", "gehen", "Mord"):
        await client.post(
            f"/api/v1/words/collections/{collection_id}/items",
            json={"item_id": str(ids[lemma])},
            headers=csrf(me),
        )

    csv_response = await client.get(f"/api/v1/words/collections/{collection_id}/export?format=csv")
    assert csv_response.status_code == 200
    assert (
        f"polyflow-de-collection-{collection_id}.csv" in csv_response.headers["content-disposition"]
    )
    csv_rows = list(csv.DictReader(io.StringIO(csv_response.text.lstrip("\ufeff"))))
    assert [row["lemma"] for row in csv_rows] == ["Haus", "gehen", "Mord"]

    anki_response = await client.get(
        f"/api/v1/words/collections/{collection_id}/export?format=anki"
    )
    assert anki_response.status_code == 200
    assert "#separator:tab" in anki_response.text
    assert [line.split("\t", 1)[0] for line in anki_response.text.splitlines()[3:]] == [
        "das Haus",
        "gehen",
        "Mord",
    ]

    child = await make_child(client, me)
    child_me = await login(client, "eva", "4321")
    child_export = await client.get(f"/api/v1/words/collections/{collection_id}/export")
    assert child_export.status_code == 404
    assert child_me["acting"]["id"] == child["id"]
