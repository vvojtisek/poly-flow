"""Generated stories: vocabulary coverage, validation, safety, one text per day, no evidence."""

import json

import httpx
import pytest
from sqlalchemy import func, select

from app.cli import LexiconRow, upsert_lexicon
from app.db.session import get_session
from app.domain import stories as dom
from app.domain.enums import BlacklistCategory, BlacklistPatternType, Language, StoryStatus
from app.main import app
from app.models import (
    ContentBlacklistEntry,
    DailyStory,
    LearningEvent,
    LexiconItem,
    User,
    UserWordProgress,
)
from app.services.llm import Llm, get_llm
from tests.helpers import csrf, login, make_child, setup_parent
from tests.test_learning import overrides as overrides


@pytest.fixture
def clock(overrides):
    return overrides


DE = Language.DE
WORDS = [
    ("ich", "PRON", "já"),
    ("sein", "VERB", "být"),
    ("und", "CCONJ", "a"),
    ("der", "DET", "ten"),
    ("ein", "DET", "jeden"),
    ("haben", "VERB", "mít"),
    ("gehen", "VERB", "jít"),
    ("Hund", "NOUN", "pes"),
    ("Haus", "NOUN", "dům"),
    ("groß", "ADJ", "velký"),
    ("spielen", "VERB", "hrát"),
    ("heute", "ADV", "dnes"),
    ("Garten", "NOUN", "zahrada"),
    ("klein", "ADJ", "malý"),
    ("Katze", "NOUN", "kočka"),
]
KNOWN = {"ich", "sein", "und", "der", "ein", "haben", "gehen", "Haus", "groß", "heute", "klein"}
TARGETS = ["Hund", "spielen", "Garten"]  # met, not known yet


def story_json(lines=None, **kw) -> str:
    body = {
        "title": "Der Hund",
        "lines": lines
        or [
            {"speaker": None, "text": "Heute ist ein großer Tag.", "cs": "Dnes je velký den."},
            {"speaker": None, "text": "Ich habe einen Hund.", "cs": "Mám psa."},
            {"speaker": None, "text": "Der Hund ist klein.", "cs": "Ten pes je malý."},
            {"speaker": None, "text": "Wir gehen in den Garten.", "cs": "Jdeme na zahradu."},
            {"speaker": None, "text": "Der Hund und ich spielen.", "cs": "Pes a já si hrajeme."},
            {"speaker": None, "text": "Das Haus ist groß.", "cs": "Ten dům je velký."},
        ],
        "glossary": [
            {"word": "Tag", "cs": "den"},
            {"word": "wir", "cs": "my"},
            {"word": "in", "cs": "v, do"},
        ],
        "names": [],
        "questions": [
            {"question": "Jaký je pes?", "options": ["velký", "malý", "starý"], "answer_index": 1},
            {
                "question": "Kam jdou?",
                "options": ["do domu", "na zahradu", "do školy"],
                "answer_index": 1,
            },
            {"question": "Jaký je dům?", "options": ["velký", "malý", "nový"], "answer_index": 0},
        ],
    }
    return json.dumps(body | kw, ensure_ascii=False)


class FakeModel:
    def __init__(self, replies: list[str]) -> None:
        self.replies = replies
        self.requests: list[dict] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(json.loads(request.content))
        text = self.replies[min(len(self.requests) - 1, len(self.replies) - 1)]
        return httpx.Response(200, json={"choices": [{"message": {"content": text}}]})


@pytest.fixture
def model():
    fake = FakeModel([f"```json\n{story_json()}\n```"])
    llm = Llm("http://ollama:11434/v1", "test-model", transport=httpx.MockTransport(fake.handler))
    app.dependency_overrides[get_llm] = lambda: llm
    yield fake


async def learner_with_words(client, *, child: bool = False) -> dict:
    parent = await setup_parent(client)
    me = parent
    if child:
        await make_child(client, parent)
        me = await login(client, "eva", "4321")
    await upsert_lexicon(
        [
            LexiconRow(language="de", rank=i + 1, lemma=w, pos=p, translation_cs=c)
            for i, (w, p, c) in enumerate(WORDS)
        ]
    )
    async for db in get_session():
        user = (await db.execute(select(User).where(User.id == me["acting"]["id"]))).scalar_one()
        items = (await db.execute(select(LexiconItem))).scalars().all()
        for item in items:
            if item.lemma == "Katze":
                continue  # never met: must not be used as a target
            db.add(
                UserWordProgress(
                    user_id=user.id,
                    lexicon_item_id=item.id,
                    first_seen_at=func.now(),
                    last_seen_at=func.now(),
                    passive_known=item.lemma in KNOWN,
                    error_count=2 if item.lemma == "Hund" else 0,
                )
            )
        await db.commit()
    return me


async def generate(client, me, kind="story"):
    return await client.post(
        "/api/v1/stories/generate", json={"language": "de", "kind": kind}, headers=csrf(me)
    )


# ---------------------------------------------------------------- domain


def test_vocabulary_folds_german_inflection():
    v = dom.Vocabulary(DE, ["sein", "haben", "spielen", "groß", "der", "Hund"])
    assert v.lemma_of("ist") == "sein" and v.lemma_of("hat") == "haben"
    assert v.lemma_of("spielt") == "spielen" and v.lemma_of("gespielt") == "spielen"
    assert v.lemma_of("großer") == "groß" and v.lemma_of("den") == "der"
    assert v.lemma_of("Hunde") == "Hund"
    assert v.lemma_of("Katze") is None


def test_parse_draft_accepts_fenced_json_and_rejects_bad_shapes():
    assert dom.parse_draft(f"Here:\n```json\n{story_json()}\n```").title == "Der Hund"
    with pytest.raises(dom.DraftInvalid, match="not_json"):
        dom.parse_draft("Es war einmal...")
    bad = json.loads(story_json())
    bad["questions"][0]["answer_index"] = 7
    with pytest.raises(dom.DraftInvalid, match="bad_shape"):
        dom.parse_draft(json.dumps(bad))


def test_coverage_needs_every_target_and_few_unknown_words():
    draft = dom.parse_draft(story_json())
    cov = dom.check_draft(DE, draft, sorted(KNOWN), TARGETS)
    assert cov.targets_missing == [] and cov.unknown_ratio <= dom.STORY_POLICY.max_unknown_ratio
    with pytest.raises(dom.DraftInvalid, match="targets_missing"):
        dom.check_draft(DE, draft, sorted(KNOWN), [*TARGETS, "Katze"])
    noisy = dom.parse_draft(
        story_json(
            lines=[
                {"text": "Der Hund spielt im Garten.", "cs": "Pes si hraje na zahradě."},
                {
                    "text": "Gestern regnete es fürchterlich lange.",
                    "cs": "Včera strašně dlouho pršelo.",
                },
                {"text": "Niemand verstand warum.", "cs": "Nikdo nechápal proč."},
                {"text": "Schließlich kam endlich Sonnenschein.", "cs": "Nakonec přišlo slunce."},
            ]
        )
    )
    with pytest.raises(dom.DraftInvalid, match="too_many_unknown_words"):
        dom.check_draft(DE, noisy, sorted(KNOWN), TARGETS)


# ---------------------------------------------------------------- API


async def test_without_a_model_the_reader_says_so(db, client):
    app.dependency_overrides[get_llm] = lambda: Llm(None, "m")
    me = await learner_with_words(client)
    r = (await client.get("/api/v1/stories/today?language=de")).json()
    assert r == {"model_available": False, "story": None}
    r = await generate(client, me)
    assert r.status_code == 409 and r.json()["detail"] == "model_unavailable"


async def test_generated_story_is_validated_stored_and_returned(db, client, model):
    me = await learner_with_words(client)
    r = await generate(client, me)
    assert r.status_code == 200, r.text
    s = r.json()
    assert s["title"] == "Der Hund" and len(s["lines"]) == 6 and s["review_status"] == "unreviewed"
    assert s["targets"][0] == "Hund"  # the most missed word leads
    assert set(s["targets"]) == set(TARGETS)
    assert all("answer_index" not in q for q in s["questions"])
    sent = json.loads(model.requests[0]["messages"][1]["content"])
    assert set(sent["target_words"]) == set(TARGETS) and "Katze" not in sent["known_words"]
    assert set(sent["known_words"]) == KNOWN
    # The same day returns the stored text without another model call.
    again = await generate(client, me, kind="dialogue")
    assert again.json()["id"] == s["id"] and len(model.requests) == 1
    today = (await client.get("/api/v1/stories/today?language=de")).json()
    assert today["model_available"] is True and today["story"]["id"] == s["id"]
    async for db_ in get_session():
        row = (await db_.execute(select(DailyStory))).scalar_one()
        assert row.status == StoryStatus.GENERATED and row.source_type == "generated"
        assert row.llm_model == "test-model" and row.llm_provider == "ollama"
        assert row.safety_checked and row.unknown_ratio is not None
        assert len(row.new_item_ids) == 3


async def test_questions_are_graded_on_the_server_and_never_evidence(db, client, model):
    me = await learner_with_words(client)
    s = (await generate(client, me)).json()
    url = f"/api/v1/stories/{s['id']}/questions/0/answer"
    r = (await client.post(url, json={"choice": 0}, headers=csrf(me))).json()
    assert r == {"correct": False, "answer_index": 1}
    r = (await client.post(url, json={"choice": 1}, headers=csrf(me))).json()
    assert r["correct"] is True
    story = (await client.get(f"/api/v1/stories/{s['id']}")).json()
    assert [q["answered"] for q in story["questions"]] == [False, None, None]  # first try kept
    bad = await client.post(
        f"/api/v1/stories/{s['id']}/questions/9/answer", json={"choice": 0}, headers=csrf(me)
    )
    assert bad.status_code == 404
    async for db_ in get_session():
        assert (await db_.execute(select(func.count()).select_from(LearningEvent))).scalar() == 0


async def test_invalid_replies_are_retried_then_fail(db, client, model):
    model.replies = ["not json at all", story_json()]
    me = await learner_with_words(client)
    r = await generate(client, me)
    assert r.status_code == 200 and len(model.requests) == 2
    async for db_ in get_session():
        row = (await db_.execute(select(DailyStory))).scalar_one()
        assert row.generation_meta["failures"] == ["not_json"]


async def test_story_missing_targets_fails_and_can_be_retried(db, client, model, clock):
    model.replies = [story_json(lines=[{"text": "Das Haus ist groß.", "cs": "Dům je velký."}] * 4)]
    me = await learner_with_words(client)
    r = await generate(client, me)
    assert r.status_code == 502 and r.json()["detail"] == "story_failed"
    assert len(model.requests) == dom.STORY_POLICY.attempts
    assert (await client.get("/api/v1/stories/today?language=de")).json()["story"] is None
    model.replies = [story_json()]
    assert (await generate(client, me)).status_code == 200


async def test_blacklisted_text_is_rejected(db, client, model):
    async for s in get_session():
        s.add(
            ContentBlacklistEntry(
                language=DE,
                pattern_type=BlacklistPatternType.KEYWORD,
                pattern="Garten",
                category=BlacklistCategory.OTHER,
            )
        )
        await s.commit()
    me = await learner_with_words(client)
    r = await generate(client, me)
    assert r.status_code == 502
    async for db_ in get_session():
        row = (await db_.execute(select(DailyStory))).scalar_one()
        assert row.status == StoryStatus.REJECTED and row.body is None


async def test_child_profile_gets_no_generated_story_by_default(db, client, model):
    me = await learner_with_words(client, child=True)
    assert (await client.get("/api/v1/stories/today?language=de")).json()[
        "model_available"
    ] is False
    r = await generate(client, me)
    assert r.status_code == 409 and r.json()["detail"] == "model_unavailable"
    assert model.requests == []


async def test_too_few_words_is_explained(db, client, model):
    me = await setup_parent(client)
    r = await generate(client, me)
    assert r.status_code == 409 and r.json()["detail"] == "not_enough_words"
    assert model.requests == []


async def test_a_new_day_brings_a_new_story_and_others_cannot_read_it(db, client, model, clock):
    me = await learner_with_words(client)
    first = (await generate(client, me)).json()
    clock.advance(days=1)
    second = (await generate(client, me)).json()
    assert second["id"] != first["id"] and len(model.requests) == 2
    await make_child(client, me, username="ota")
    await login(client, "ota", "4321")
    assert (await client.get(f"/api/v1/stories/{first['id']}")).status_code == 404
    assert (await client.get(f"/api/v1/stories/{first['id']}/audio?line=0")).status_code == 404
