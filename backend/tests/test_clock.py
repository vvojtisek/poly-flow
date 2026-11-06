"""Telling the time: spoken forms pinned per language, Czech anchors, distractors, the quiz API."""

import pytest

from app.domain.clock import MINUTES, Time, czech, distractors, say
from tests.helpers import setup_parent

# fmt: off
CASES = {
    "de": {(3, 0): "drei Uhr", (1, 0): "ein Uhr", (3, 5): "fünf nach drei",
           (3, 15): "Viertel nach drei", (3, 20): "zwanzig nach drei",
           (3, 25): "fünf vor halb vier", (3, 30): "halb vier", (3, 35): "fünf nach halb vier",
           (3, 40): "zwanzig vor vier", (3, 45): "Viertel vor vier", (3, 55): "fünf vor vier",
           (12, 30): "halb eins", (12, 5): "fünf nach zwölf", (1, 10): "zehn nach eins"},
    "fr": {(3, 0): "trois heures", (1, 0): "une heure", (12, 0): "midi",
           (3, 5): "trois heures cinq", (3, 15): "trois heures et quart",
           (3, 30): "trois heures et demie", (12, 30): "midi et demi",
           (3, 35): "quatre heures moins vingt-cinq", (3, 45): "quatre heures moins le quart",
           (12, 45): "une heure moins le quart", (11, 45): "midi moins le quart"},
    "it": {(3, 0): "sono le tre", (1, 0): "è l'una", (12, 0): "è mezzogiorno",
           (3, 15): "sono le tre e un quarto", (3, 30): "sono le tre e mezza",
           (3, 20): "sono le tre e venti", (3, 40): "sono le quattro meno venti",
           (3, 45): "sono le quattro meno un quarto", (12, 45): "è l'una meno un quarto",
           (1, 30): "è l'una e mezza"},
    "en": {(3, 0): "three o'clock", (3, 5): "five past three", (3, 15): "quarter past three",
           (3, 25): "twenty-five past three", (3, 30): "half past three",
           (3, 35): "twenty-five to four", (3, 45): "quarter to four", (12, 50): "ten to one"},
}
# fmt: on


@pytest.mark.parametrize(
    ("language", "hm", "phrase"),
    [(lang, hm, p) for lang, c in CASES.items() for hm, p in c.items()],
)
def test_phrases(language, hm, phrase):
    assert say(Time(*hm), language) == phrase


def test_every_time_has_a_phrase():
    for lang in CASES:
        phrases = {say(Time(h, m), lang) for h in range(1, 13) for m in MINUTES}
        assert len(phrases) == 144  # no two times read the same


def test_czech_anchor():
    assert czech(Time(3, 15)) == "čtvrt na čtyři"
    assert czech(Time(3, 30)) == "půl čtvrté"
    assert czech(Time(3, 45)) == "tři čtvrtě na čtyři"
    assert czech(Time(1, 0)) == "jedna hodina" and czech(Time(4, 0)) == "čtyři hodiny"
    assert czech(Time(5, 0)) == "pět hodin" and czech(Time(12, 30)) == "půl jedné"
    assert czech(Time(3, 5)) == "3:05"


def test_distractors_and_validation():
    t = Time(3, 15)
    d = distractors(t)
    assert d[0] == Time(2, 15)  # "čtvrt na tři" thinking
    assert t not in d and len(d) == len(set(d)) and len(d) >= 3
    for h in range(1, 13):
        for m in MINUTES:
            assert len(distractors(Time(h, m))) >= 3
    assert Time(12, 55).shifted(5) == Time(1, 0)
    with pytest.raises(ValueError):
        Time(13, 0)
    with pytest.raises(ValueError):
        Time(3, 7)


async def test_quiz_api(db, client):
    await setup_parent(client)
    for level in ("quarters", "five"):
        q = (
            await client.get("/api/v1/clock/quiz", params={"language": "de", "level": level})
        ).json()
        assert len(q["options"]) == 4
        right = q["options"][q["answer"]]
        assert (right["hour"], right["minute"]) == (q["time"]["hour"], q["time"]["minute"])
        assert len({o["phrase"] for o in q["options"]}) == 4
        if level == "quarters":
            assert q["time"]["minute"] in (0, 15, 30, 45)
    bad = await client.get("/api/v1/clock/audio", params={"hour": 3, "minute": 7})
    assert bad.status_code == 422


async def test_quiz_requires_login(db, client):
    assert (await client.get("/api/v1/clock/quiz")).status_code == 401
