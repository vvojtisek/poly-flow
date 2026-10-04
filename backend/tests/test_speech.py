"""Spoken answers (policy v3): transcript matching, the Whisper client, and the endpoint."""

import httpx
import pytest
from sqlalchemy import select

from app.api.deps import get_limiter
from app.api.learning import get_now
from app.db.session import get_session
from app.domain.enums import Language
from app.domain.learning_policy import POLICY
from app.domain.speech import SpokenWord, judge
from app.main import app
from app.models import LearningEvent
from app.services.rate_limit import MemoryAttemptLimiter
from app.services.stt import Stt, SttRejected, SttUnavailable, get_stt
from tests.helpers import Clock, csrf, seed_words
from tests.test_learning import (
    answer,
    checkable,
    child_session,
    key,
    next_task,
    progress_rows,
    start,
)

W = SpokenWord


@pytest.mark.parametrize(
    ("language", "lemma", "said", "matched"),
    [
        (Language.DE, "Hund", ["Der", "Hund."], True),
        (Language.DE, "Hund", ["hund"], True),
        (Language.DE, "Straße", ["Strasse"], True),  # casefold: ß == ss
        (Language.DE, "der", ["der"], True),  # an article that is itself the word
        (Language.EN, "go", ["to", "go"], True),
        (Language.FR, "école", ["l'école"], True),
        (Language.IT, "amica", ["un'amica"], True),
        (Language.DE, "Hund", ["Hund", "Katze"], False),  # several guesses at once
        (Language.DE, "Hund", ["Hand"], False),
        (Language.DE, "Hund", [], False),  # silence
        (Language.FR, "école", ["ecole"], False),  # a different transcript, not a near miss
    ],
)
def test_judge(language, lemma, said, matched):
    verdict = judge(language, lemma, [W(w, 0.9) for w in said])
    assert verdict.matched is matched
    assert verdict.confidence == (0.9 if matched else None)


def test_judge_confidence_is_the_least_sure_word():
    v = judge(Language.EN, "ice cream", [W(" Ice", 0.95), W(" cream", 0.41)])
    assert v.matched and v.confidence == 0.41


# ---------------------------------------------------------------- Whisper client


def whisper(status=200, body=None, seen=None):
    def handler(request: httpx.Request) -> httpx.Response:
        if seen is not None:
            seen.append(request)
        if isinstance(status, Exception):
            raise status
        return httpx.Response(status, json=body if body is not None else {"words": []})

    return Stt(
        "http://whisper:9000", client=httpx.AsyncClient(transport=httpx.MockTransport(handler))
    )


async def test_stt_sends_language_and_audio_but_no_prompt():
    seen: list[httpx.Request] = []
    stt = whisper(body={"words": [{"word": " Hund", "probability": 0.8, "start": 0}]}, seen=seen)
    words = await stt.transcribe(Language.DE, b"OggS-audio", "audio/ogg")
    assert words == [W(" Hund", 0.8)]
    sent = seen[0].content
    assert b'name="language"\r\n\r\nde' in sent and b"OggS-audio" in sent
    assert b"initial_prompt" not in sent  # never suggest the expected word


@pytest.mark.parametrize(
    ("status", "error", "code"),
    [
        (413, SttRejected, "audio_too_long"),
        (422, SttRejected, "audio_invalid"),
        (500, SttUnavailable, None),
        (httpx.ConnectError("refused"), SttUnavailable, None),
    ],
)
async def test_stt_errors(status, error, code):
    with pytest.raises(error) as exc:
        await whisper(status=status).transcribe(Language.DE, b"x", "audio/webm")
    if code:
        assert exc.value.code == code


# ---------------------------------------------------------------- endpoint


class FakeStt:
    def __init__(self) -> None:
        self.words: list[SpokenWord] = []
        self.calls = 0
        self.down = False

    async def transcribe(self, language, audio, content_type):
        self.calls += 1
        if self.down:
            raise SttUnavailable("whisper_unreachable")
        return self.words


@pytest.fixture
def stt():
    fake = FakeStt()
    clock = Clock()
    lim = MemoryAttemptLimiter()
    app.dependency_overrides[get_stt] = lambda: fake
    app.dependency_overrides[get_now] = lambda: clock.now
    app.dependency_overrides[get_limiter] = lambda: lim
    yield fake, clock
    app.dependency_overrides.clear()


async def speak(client, me, task, k=None, body=b"webm-bytes", content_type="audio/webm"):
    return await client.post(
        f"/api/v1/learning/tasks/{task['id']}/speech",
        params={"idempotency_key": k or key()},
        content=body,
        headers={**csrf(me), "Content-Type": content_type},
    )


async def spoken_events() -> list[LearningEvent]:
    async for db in get_session():
        return list(
            (
                await db.execute(select(LearningEvent).where(LearningEvent.answer_mode == "spoken"))
            ).scalars()
        )
    return []


async def recall_in_check(client, stt):
    _, clock = stt
    await seed_words(words=[("Haus", "NOUN", "dům")])
    me = await child_session(client)
    s = await checkable(client, me, clock)
    t = await next_task(client, s["id"])
    assert t["type"] == "recall"
    return me, t


async def test_confident_spoken_word_is_active_evidence(db, client, stt):
    me, t = await recall_in_check(client, stt)
    stt[0].words = [W(" Das", 0.9), W(" Haus.", 0.8)]
    r = await speak(client, me, t)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["verdict"] == "spoken" and body["correct"] and body["counted"]
    assert body["task_done"] and body["heard"] == "Das Haus." and body["expected"] == "Haus"
    p = (await progress_rows())["Haus"]
    assert p.correct_count == 1 and p.phonetic_score is None
    assert p.orthography_score is None  # speech says nothing about spelling
    [ev] = await spoken_events()
    assert ev.is_correct and ev.counts_as_evidence and ev.transcript_confidence == 0.8
    assert ev.answer == "Das Haus." and ev.task_type == "recall" and ev.policy_version == "v3"


@pytest.mark.parametrize(
    "words",
    [
        [W("Haus", POLICY.spoken_min_confidence - 0.01)],  # unsure transcript
        [W("Maus", 0.95)],  # another word
        [],  # silence
    ],
)
async def test_unconfirmed_speech_changes_nothing(db, client, stt, words):
    me, t = await recall_in_check(client, stt)
    stt[0].words = words
    body = (await speak(client, me, t)).json()
    assert body["verdict"] == "not_understood" and not body["correct"] and not body["counted"]
    assert not body["task_done"] and body["can_retry"] and body["attempts"] == 0
    assert body["expected"] is None  # the check is still open
    p = (await progress_rows())["Haus"]
    assert p.error_count == 0 and p.correct_count == 0
    [ev] = await spoken_events()  # kept to calibrate the threshold
    assert not ev.is_correct and not ev.counts_as_evidence and ev.verdict == "not_understood"
    # Typing the word afterwards is still the first, counted attempt.
    typed = (await answer(client, me, t, {"text": "Haus"})).json()
    assert typed["counted"] and typed["attempts"] == 1


async def test_speech_replays_without_transcribing_again(db, client, stt):
    me, t = await recall_in_check(client, stt)
    stt[0].words = [W("Haus", 0.9)]
    k = key()
    first = (await speak(client, me, t, k)).json()
    again = await speak(client, me, t, k)
    assert again.status_code == 200 and again.json() == first
    assert stt[0].calls == 1 and len(await spoken_events()) == 1


async def test_speech_only_answers_recall_tasks(db, client, stt):
    fake, _ = stt
    await seed_words()
    me = await child_session(client)
    s = await start(client, me)
    t = await next_task(client, s["id"])
    assert t["type"] == "recognition"
    fake.words = [W("der", 0.9)]
    r = await speak(client, me, t)
    assert r.status_code == 422 and r.json()["detail"] == "speech_not_supported"


async def test_speech_request_errors(db, client, stt):
    me, t = await recall_in_check(client, stt)
    r = await speak(client, me, t, content_type="application/json", body=b"{}")
    assert r.status_code == 415
    r = await speak(client, me, t, body=b"x" * (1024 * 1024 + 1))
    assert r.status_code == 413
    r = await speak(client, me, t, body=b"")
    assert r.status_code == 422
    stt[0].down = True
    r = await speak(client, me, t)
    assert r.status_code == 503 and r.json()["detail"] == "speech_unavailable"
    no_csrf = await client.post(
        f"/api/v1/learning/tasks/{t['id']}/speech",
        params={"idempotency_key": key()},
        content=b"x",
        headers={"Content-Type": "audio/webm"},
    )
    assert no_csrf.status_code == 403
    assert (await progress_rows())["Haus"].error_count == 0
