"""Speech for lesson content: Piper client, disk cache, and the learning audio endpoints."""

import json
import re
from pathlib import Path

import httpx
import pytest

from app.api.deps import get_limiter
from app.api.learning import get_now
from app.domain.enums import Language
from app.main import app
from app.services.rate_limit import MemoryAttemptLimiter
from app.services.tts import VOICES, Tts, TtsUnavailable, get_tts
from tests.helpers import PARENT, Clock, csrf, login, make_child
from tests.test_learning import answer, child_session, correct_answer, next_task, start
from tests.test_scenes import seed

REPO = Path(__file__).resolve().parents[2]
WAV = b"RIFF\x24\x00\x00\x00WAVEfmt " + bytes(28)


class FakePiper:
    """Piper's HTTP API: GET /voices, POST /synthesize."""

    def __init__(self) -> None:
        self.voices = {v: {"audio": {"sample_rate": 22050}} for v in VOICES.values()}
        self.synthesized: list[dict] = []
        self.down = False
        self.body = WAV

    def handler(self, request: httpx.Request) -> httpx.Response:
        if self.down:
            raise httpx.ConnectError("refused", request=request)
        if request.url.path == "/voices":
            return httpx.Response(200, json=self.voices)
        self.synthesized.append(json.loads(request.content))
        return httpx.Response(200, content=self.body)


@pytest.fixture
def piper() -> FakePiper:
    return FakePiper()


def make_tts(piper: FakePiper, cache: Path) -> Tts:
    client = httpx.AsyncClient(transport=httpx.MockTransport(piper.handler))
    return Tts("http://piper:5000", cache, client=client)


async def test_speech_is_cached_on_disk(piper, tmp_path):
    tts = make_tts(piper, tmp_path)
    first = await tts.speech(Language.DE, "  der   Hund ")
    again = await tts.speech(Language.DE, "der Hund")
    assert first == again and first.read_bytes() == WAV
    assert piper.synthesized == [{"text": "der Hund", "voice": "de_DE-thorsten-medium"}]
    # A fresh process (another API worker, a restart) reuses the same file.
    assert await make_tts(piper, tmp_path).speech(Language.DE, "der Hund") == first
    assert len(piper.synthesized) == 1
    assert not list(tmp_path.rglob(".tmp-*"))


async def test_voice_language_and_text_select_the_file(piper, tmp_path):
    tts = make_tts(piper, tmp_path)
    de = await tts.speech(Language.DE, "Hallo")
    en = await tts.speech(Language.EN, "Hallo")
    other = await tts.speech(Language.DE, "Hallo!")
    assert len({de, en, other}) == 3
    assert [s["voice"] for s in piper.synthesized] == [
        "de_DE-thorsten-medium",
        "en_GB-jenny_dioco-medium",
        "de_DE-thorsten-medium",
    ]


async def test_new_voice_revision_is_synthesized_afresh(piper, tmp_path):
    old = await make_tts(piper, tmp_path).speech(Language.FR, "le chien")
    piper.voices["fr_FR-siwis-medium"] = {"audio": {"sample_rate": 16000}}
    new = await make_tts(piper, tmp_path).speech(Language.FR, "le chien")
    assert new != old and len(piper.synthesized) == 2


async def test_missing_voice_is_refused_not_replaced(piper, tmp_path):
    # Piper would answer with its default voice, i.e. the wrong language.
    del piper.voices["it_IT-paola-medium"]
    with pytest.raises(TtsUnavailable):
        await make_tts(piper, tmp_path).speech(Language.IT, "il cane")
    assert piper.synthesized == []


async def test_piper_down(piper, tmp_path):
    tts = make_tts(piper, tmp_path)
    cached = await tts.speech(Language.DE, "Hallo")
    piper.down = True
    # Known voices: the cache keeps working; new text cannot be synthesized.
    assert await tts.speech(Language.DE, "Hallo") == cached
    with pytest.raises(TtsUnavailable):
        await tts.speech(Language.DE, "Tschüss")
    # A process that never reached Piper cannot tell which voice revision is current.
    with pytest.raises(TtsUnavailable):
        await make_tts(piper, tmp_path).speech(Language.DE, "Hallo")


async def test_non_audio_response_is_not_cached(piper, tmp_path):
    piper.body = b"<html>error</html>"
    tts = make_tts(piper, tmp_path)
    with pytest.raises(TtsUnavailable):
        await tts.speech(Language.DE, "Hallo")
    assert not list(tmp_path.rglob("*.wav"))


async def test_unwritable_cache_means_no_sound_not_an_error(piper, tmp_path):
    blocker = tmp_path / "cache"
    blocker.write_text("a file where the cache directory should be")
    with pytest.raises(TtsUnavailable):
        await make_tts(piper, blocker).speech(Language.DE, "Hallo")


async def test_text_limits(piper, tmp_path):
    tts = make_tts(piper, tmp_path)
    for text in ("   ", "x" * 401):
        with pytest.raises(ValueError):
            await tts.speech(Language.DE, text)


def test_voices_match_the_piper_image_and_model_spec():
    dockerfile = (REPO / "docker" / "piper" / "Dockerfile").read_text()
    image = set(re.search(r'PIPER_VOICES="([^"]+)"', dockerfile).group(1).split())
    spec = json.loads((REPO / "docker" / "models" / "models.spec.json").read_text())
    locked = {
        m["name"].removeprefix("piper/") for m in spec["models"] if m["name"].startswith("piper/")
    }
    assert set(VOICES) == set(Language)
    assert set(VOICES.values()) <= image <= locked


# ---------------------------------------------------------------- endpoints


class RecordingTts:
    def __init__(self, cache: Path) -> None:
        self.cache = cache
        self.spoken: list[tuple[Language, str]] = []
        self.down = False

    async def speech(self, language: Language, text: str) -> Path:
        if self.down:
            raise TtsUnavailable("piper_unreachable")
        self.spoken.append((language, text))
        path = self.cache / f"{len(self.spoken)}.wav"
        path.write_bytes(WAV)
        return path


@pytest.fixture
def tts(tmp_path):
    fake = RecordingTts(tmp_path)
    clock = Clock()
    lim = MemoryAttemptLimiter()
    app.dependency_overrides[get_tts] = lambda: fake
    app.dependency_overrides[get_now] = lambda: clock.now
    app.dependency_overrides[get_limiter] = lambda: lim
    yield fake
    app.dependency_overrides.clear()


async def test_lesson_scene_and_word_cards_are_spoken(db, client, tts):
    await seed()
    me = await child_session(client)
    s = await start(client, me)
    base = f"/api/v1/learning/sessions/{s['id']}/audio"

    r = await client.get(base, params={"line": 1})
    assert r.status_code == 200 and r.headers["content-type"] == "audio/wav"
    assert r.content == WAV
    sein = next(c for c in s["words"] if c["lemma"] == "sein")
    assert (await client.get(base, params={"item": sein["id"]})).status_code == 200
    r = await client.get(base, params={"item": sein["id"], "part": "context"})
    assert r.status_code == 200
    assert tts.spoken == [
        (Language.DE, "Ich bin Tom. Und du?"),
        (Language.DE, "sein"),
        (Language.DE, "Ich bin Tom. Und du?"),
    ]

    for params in ({"line": 3}, {"item": s["id"]}, {}, {"line": 0, "item": sein["id"]}):
        assert (await client.get(base, params=params)).status_code in (404, 422), params


async def test_task_audio_never_gives_a_recall_answer_away(db, client, tts):
    await seed()
    me = await child_session(client)
    s = await start(client, me)
    t = await next_task(client, s["id"])
    assert t["type"] == "recognition"
    r = await client.get(f"/api/v1/learning/tasks/{t['id']}/audio")
    assert r.status_code == 200 and tts.spoken[-1] == (Language.DE, t["prompt"])

    while t["type"] != "recall":
        assert (await answer(client, me, t, await correct_answer(t))).status_code == 200
        t = await next_task(client, s["id"])
    url = f"/api/v1/learning/tasks/{t['id']}/audio"
    r = await client.get(url)
    assert r.status_code == 409 and r.json()["detail"] == "audio_would_reveal"
    spoken = len(tts.spoken)
    assert (await answer(client, me, t, await correct_answer(t))).json()["task_done"]
    assert (await client.get(url)).status_code == 200  # the answer, after the task
    assert len(tts.spoken) == spoken + 1


async def test_audio_belongs_to_the_session_owner(db, client, tts):
    await seed()
    me = await child_session(client)
    s = await start(client, me)
    t = await next_task(client, s["id"])
    parent = await login(client, PARENT["username"], PARENT["password"])
    await make_child(client, parent, username="ota", pin="9876")
    await login(client, "ota", "9876")
    assert (
        await client.get(f"/api/v1/learning/sessions/{s['id']}/audio?line=0")
    ).status_code == 404
    assert (await client.get(f"/api/v1/learning/tasks/{t['id']}/audio")).status_code == 404
    assert tts.spoken == []


async def test_audio_unavailable(db, client, tts):
    await seed()
    me = await child_session(client)
    s = await start(client, me)
    tts.down = True
    r = await client.get(f"/api/v1/learning/sessions/{s['id']}/audio?line=0")
    assert r.status_code == 503 and r.json()["detail"] == "audio_unavailable"
    assert csrf(me)  # the session itself is untouched
    assert (await next_task(client, s["id"]))["type"] == "recognition"
