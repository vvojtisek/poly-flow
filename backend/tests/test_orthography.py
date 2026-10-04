import pytest

from app.domain.enums import Language
from app.domain.orthography import Verdict, check_spelling

DE, FR, IT, EN = Language.DE, Language.FR, Language.IT, Language.EN


@pytest.mark.parametrize(
    ("lang", "expected", "answer", "pos", "verdict"),
    [
        (DE, "Haus", "Haus", "NOUN", Verdict.EXACT),
        (DE, "Haus", "  Haus. ", "NOUN", Verdict.EXACT),
        (DE, "Haus", "das Haus", "NOUN", Verdict.EXACT),  # article allowed
        (DE, "Haus", "haus", "NOUN", Verdict.CASE),  # German nouns are capitalised
        (DE, "gehen", "Gehen", "VERB", Verdict.EXACT),  # not significant for verbs
        (DE, "Straße", "Strasse", "NOUN", Verdict.VARIANT),
        (DE, "schön", "schoen", "ADJ", Verdict.VARIANT),
        (DE, "Größe", "Groesse", "NOUN", Verdict.VARIANT),  # two substitutions at once
        (DE, "schön", "schon", "ADJ", Verdict.DIACRITICS),
        (DE, "Haus", "Maus", "NOUN", Verdict.WRONG),
        (DE, "Haus", "", "NOUN", Verdict.WRONG),
        (FR, "école", "ecole", "NOUN", Verdict.DIACRITICS),
        (FR, "école", "l'école", "NOUN", Verdict.EXACT),
        (FR, "école", "l" + chr(0x2019) + "école", "NOUN", Verdict.EXACT),  # typographic apostrophe
        (FR, "cœur", "coeur", "NOUN", Verdict.VARIANT),
        (FR, "le", "le", "DET", Verdict.EXACT),  # article lemma is not stripped away
        (IT, "città", "citta", "NOUN", Verdict.DIACRITICS),
        (IT, "città", "la città", "NOUN", Verdict.EXACT),
        (IT, "perché", "perche", "ADV", Verdict.DIACRITICS),
        (EN, "dog", "the dog", "NOUN", Verdict.EXACT),
        (EN, "apple", "an apple", "NOUN", Verdict.EXACT),
        (EN, "go", "to go", "VERB", Verdict.EXACT),  # infinitive marker allowed
        (EN, "to", "to", "ADP", Verdict.EXACT),  # the lemma itself is not stripped
        (EN, "house", "House", "NOUN", Verdict.EXACT),  # no capitalisation rule
        (EN, "I", "i", "PRON", Verdict.EXACT),
        (EN, "house", "horse", "NOUN", Verdict.WRONG),
    ],
)
def test_verdicts(lang, expected, answer, pos, verdict):
    assert check_spelling(lang, expected, answer, pos).verdict is verdict


def test_correctness_and_scores():
    assert check_spelling(DE, "Haus", "Haus", "NOUN").correct
    assert check_spelling(DE, "Straße", "Strasse", "NOUN").correct
    case = check_spelling(DE, "Haus", "haus", "NOUN")
    assert not case.correct and case.note == "de_noun_capital" and 0 < case.score < 1
    assert not check_spelling(FR, "école", "ecole", "NOUN").correct


def test_nfd_input_is_normalised():
    decomposed = "école"  # e + combining acute
    assert check_spelling(FR, "école", decomposed, "NOUN").verdict is Verdict.EXACT
