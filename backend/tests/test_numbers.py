"""Number trainer: spelling rules pinned per language, and the practice endpoints."""

import pytest

from app.domain.numbers import MAX, accepted, check, parse_digits, spell
from tests.helpers import csrf, setup_parent

# fmt: off
CASES = {
    "de": {
        0: "null", 1: "eins", 16: "sechzehn", 17: "siebzehn", 21: "einundzwanzig",
        30: "dreißig", 77: "siebenundsiebzig", 100: "hundert", 101: "hunderteins",
        116: "hundertsechzehn", 200: "zweihundert", 1000: "tausend", 1001: "tausendeins",
        1999: "tausendneunhundertneunundneunzig", 2024: "zweitausendvierundzwanzig",
        6000: "sechstausend", 7070: "siebentausendsiebzig",
    },
    "fr": {
        0: "zéro", 17: "dix-sept", 21: "vingt et un", 22: "vingt-deux", 61: "soixante et un",
        70: "soixante-dix", 71: "soixante et onze", 72: "soixante-douze", 80: "quatre-vingts",
        81: "quatre-vingt-un", 90: "quatre-vingt-dix", 91: "quatre-vingt-onze",
        99: "quatre-vingt-dix-neuf", 100: "cent", 101: "cent un", 200: "deux cents",
        201: "deux cent un", 280: "deux cent quatre-vingts", 1000: "mille",
        2000: "deux mille", 2024: "deux mille vingt-quatre",
    },
    "it": {
        0: "zero", 17: "diciassette", 21: "ventuno", 23: "ventitré", 28: "ventotto",
        38: "trentotto", 100: "cento", 101: "centouno", 103: "centotré", 108: "centotto",
        180: "centottanta", 200: "duecento", 1000: "mille", 1001: "milleuno",
        2000: "duemila", 2024: "duemilaventiquattro", 1080: "milleottanta",
    },
    "en": {
        0: "zero", 13: "thirteen", 21: "twenty-one", 40: "forty", 100: "one hundred",
        101: "one hundred and one", 115: "one hundred and fifteen", 1000: "one thousand",
        1001: "one thousand and one", 1999: "one thousand nine hundred and ninety-nine",
        2024: "two thousand and twenty-four", 3400: "three thousand four hundred",
    },
}
# fmt: on


@pytest.mark.parametrize(
    ("language", "n", "words"), [(lang, n, w) for lang, c in CASES.items() for n, w in c.items()]
)
def test_spelling(language, n, words):
    assert spell(n, language) == words
    assert check(n, words, language)


@pytest.mark.parametrize(
    ("language", "n", "answer"),
    [
        ("de", 100, "einhundert"),
        ("de", 1100, "elfhundert"),
        ("de", 1100, "tausendeinhundert"),
        ("de", 1999, "Neunzehnhundertneunundneunzig"),
        ("fr", 21, "vingt-et-un"),  # 1990 reform
        ("fr", 201, "deux-cent-un"),
        ("fr", 1200, "douze cents"),
        ("it", 108, "centootto"),
        ("it", 101, "centuno"),
        ("it", 23, "ventitre"),
        ("en", 101, "a hundred and one"),
        ("en", 101, "one hundred one"),
        ("en", 1100, "eleven hundred"),
        ("en", 21, "  twenty one "),
    ],
)
def test_accepted_alternatives(language, n, answer):
    assert check(n, answer, language)


@pytest.mark.parametrize(
    ("language", "n", "answer"),
    [
        ("fr", 80, "quatre-vingt"),  # 80 takes an s
        ("fr", 81, "quatre-vingts-un"),
        ("fr", 200, "deux cent"),
        ("de", 21, "zwanzigeins"),
        ("de", 1, "ein"),
        ("it", 21, "ventiuno"),
        ("en", 1999, "nineteen hundred"),
        ("en", 40, "fourty"),
    ],
)
def test_rejected(language, n, answer):
    assert not check(n, answer, language)


def test_every_number_spells_and_is_accepted():
    for lang in CASES:
        for n in range(MAX + 1):
            assert check(n, spell(n, lang), lang)
    assert all(" " not in f for f in accepted(1234, "de"))


def test_range_and_digits():
    with pytest.raises(ValueError):
        spell(MAX + 1, "de")
    assert parse_digits(" 1 999 ") == 1999
    assert parse_digits("2.024") == 2024
    assert (
        parse_digits("12a") is None and parse_digits("") is None and parse_digits("10000") is None
    )


async def test_number_endpoints(db, client):
    me = await setup_parent(client)
    r = await client.get("/api/v1/numbers/spell", params={"n": 71, "language": "fr"})
    assert r.json() == {"n": 71, "words": "soixante et onze"}
    assert (await client.get("/api/v1/numbers/spell", params={"n": 10000})).status_code == 422
    ok = await client.post(
        "/api/v1/numbers/check",
        json={"language": "de", "n": 21, "answer": "einundzwanzig"},
        headers=csrf(me),
    )
    assert ok.json() == {"correct": True, "n": 21, "words": "einundzwanzig"}
    bad = await client.post(
        "/api/v1/numbers/check",
        json={"language": "de", "n": 21, "answer": "zwanzigeins"},
        headers=csrf(me),
    )
    assert bad.json()["correct"] is False and bad.json()["words"] == "einundzwanzig"
    read = await client.post(
        "/api/v1/numbers/check",
        json={"language": "it", "n": 1080, "answer": "1080", "direction": "read"},
        headers=csrf(me),
    )
    assert read.json()["correct"] is True


async def test_numbers_require_login(db, client):
    assert (await client.get("/api/v1/numbers/spell", params={"n": 1})).status_code == 401
