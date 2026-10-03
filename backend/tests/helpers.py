"""Shared helpers for DB-backed API tests."""

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from app.cli import LexiconRow, upsert_lexicon

PARENT = {"username": "mama", "display_name": "Máma", "password": "correct horse 1"}


def csrf(me: dict) -> dict:
    return {"X-CSRF-Token": me["csrf_token"]}


@dataclass
class Clock:
    now: datetime = field(default_factory=lambda: datetime(2026, 10, 5, 8, 0, tzinfo=UTC))

    def advance(self, **kw) -> None:
        self.now += timedelta(**kw)


async def setup_parent(client) -> dict:
    r = await client.post("/api/v1/setup", json=PARENT)
    assert r.status_code == 201, r.text
    return r.json()


async def make_child(client, parent_me: dict, username: str = "eva", pin: str = "4321") -> dict:
    r = await client.post(
        "/api/v1/profiles",
        json={"username": username, "display_name": username.title(), "kind": "child", "pin": pin},
        headers=csrf(parent_me),
    )
    assert r.status_code == 201, r.text
    return r.json()


async def login(client, username: str, secret: str) -> dict:
    client.cookies.clear()
    r = await client.post("/api/v1/auth/login", json={"username": username, "secret": secret})
    assert r.status_code == 200, r.text
    return r.json()


WORDS = {
    "de": [
        ("der", "DET", "ten"),
        ("und", "CCONJ", "a"),
        ("Haus", "NOUN", "dům"),
        ("Straße", "NOUN", "ulice"),
        ("gehen", "VERB", "jít"),
        ("schön", "ADJ", "hezký"),
    ],
    "fr": [("le", "DET", "ten"), ("et", "CCONJ", "a"), ("école", "NOUN", "škola")],
}


async def seed_words(lang: str = "de", words=None) -> None:
    rows = [
        LexiconRow(language=lang, rank=i + 1, lemma=w, pos=pos, translation_cs=cs)
        for i, (w, pos, cs) in enumerate(words or WORDS[lang])
    ]
    await upsert_lexicon(rows)
