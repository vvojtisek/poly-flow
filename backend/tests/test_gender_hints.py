import pytest

from app.domain.enums import Language
from app.domain.gender_hints import hint, normalise

DE, FR, IT = Language.DE, Language.FR, Language.IT


@pytest.mark.parametrize(
    ("lang", "lemma", "gender", "suffix", "rule", "exception"),
    [
        (DE, "Zeitung", "die", "ung", "die", False),
        (DE, "Mädchen", "das", "chen", "das", False),
        (DE, "Freiheit", "die", "heit", "die", False),
        (DE, "Lehrling", "der", "ling", "der", False),
        (DE, "Blume", "die", "e", "die", False),
        (DE, "Junge", "der", "e", "die", True),
        (DE, "Moment", "der", "ment", "das", True),
        (DE, "Museum", "das", "um", "das", False),
        (DE, "Musik", "die", "ik", "die", False),
        (FR, "question", "f", "tion", "f", False),
        (FR, "bateau", "m", "eau", "m", False),
        (FR, "plage", "f", "age", "m", True),
        (IT, "libro", "m", "o", "m", False),
        (IT, "mano", "f", "o", "m", True),
        (IT, "problema", "m", "a", "f", True),
        (IT, "città", "f", "tà", "f", False),
        (IT, "stazione", "f", "zione", "f", False),
    ],
)
def test_rules(lang, lemma, gender, suffix, rule, exception):
    h = hint(lang, lemma, gender)
    assert h is not None
    assert (h.suffix, h.gender, h.exception) == (suffix, rule, exception)


def test_short_words_and_no_rule():
    assert hint(DE, "Baum", "der") is None  # -um needs a longer word
    assert hint(DE, "Ei", "das") is None
    assert hint(DE, "Tisch", "der") is None
    assert hint(IT, "cane", "m") is None  # -e is ambiguous in Italian
    assert hint(Language.EN, "house", None) is None


def test_normalise():
    assert normalise(DE, "Der") == "der"
    assert normalise(FR, "m/f") is None
    assert normalise(IT, "f") == "f"
    assert normalise(DE, None) is None
