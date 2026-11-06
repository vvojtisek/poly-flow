import pytest

from app.domain.declension import (
    CASES,
    DETS,
    GENDERS,
    adjective_ending,
    adjective_stem,
    determiner,
    genitive_singular,
    phrase,
    signal_on,
)

# Reference paradigm with "klein" (rows: case; columns m, f, n, pl), as in standard grammars.
PARADIGM = {
    "def": {
        "nom": ["der kleine", "die kleine", "das kleine", "die kleinen"],
        "akk": ["den kleinen", "die kleine", "das kleine", "die kleinen"],
        "dat": ["dem kleinen", "der kleinen", "dem kleinen", "den kleinen"],
        "gen": ["des kleinen", "der kleinen", "des kleinen", "der kleinen"],
    },
    "indef": {
        "nom": ["ein kleiner", "eine kleine", "ein kleines", "kleine"],
        "akk": ["einen kleinen", "eine kleine", "ein kleines", "kleine"],
        "dat": ["einem kleinen", "einer kleinen", "einem kleinen", "kleinen"],
        "gen": ["eines kleinen", "einer kleinen", "eines kleinen", "kleiner"],
    },
    "kein": {
        "nom": ["kein kleiner", "keine kleine", "kein kleines", "keine kleinen"],
        "akk": ["keinen kleinen", "keine kleine", "kein kleines", "keine kleinen"],
        "dat": ["keinem kleinen", "keiner kleinen", "keinem kleinen", "keinen kleinen"],
        "gen": ["keines kleinen", "keiner kleinen", "keines kleinen", "keiner kleinen"],
    },
    "poss": {
        "nom": ["mein kleiner", "meine kleine", "mein kleines", "meine kleinen"],
        "akk": ["meinen kleinen", "meine kleine", "mein kleines", "meine kleinen"],
        "dat": ["meinem kleinen", "meiner kleinen", "meinem kleinen", "meinen kleinen"],
        "gen": ["meines kleinen", "meiner kleinen", "meines kleinen", "meiner kleinen"],
    },
    "none": {
        "nom": ["kleiner", "kleine", "kleines", "kleine"],
        "akk": ["kleinen", "kleine", "kleines", "kleine"],
        "dat": ["kleinem", "kleiner", "kleinem", "kleinen"],
        "gen": ["kleinen", "kleiner", "kleinen", "kleiner"],
    },
}


@pytest.mark.parametrize("det", DETS)
@pytest.mark.parametrize("case", CASES)
def test_full_paradigm(det, case):
    for gender, expected in zip(GENDERS, PARADIGM[det][case], strict=True):
        d = determiner(det, case, gender)
        ending, _ = adjective_ending(det, case, gender)
        got = " ".join(x for x in ((d.text if d else ""), "klein" + ending) if x)
        assert got == expected, (det, case, gender)


def test_declension_kind_and_signal():
    assert adjective_ending("def", "nom", "m") == ("e", "weak")
    assert adjective_ending("indef", "nom", "m") == ("er", "mixed")
    assert adjective_ending("indef", "dat", "m") == ("en", "mixed")
    assert adjective_ending("none", "dat", "f") == ("er", "strong")
    assert adjective_ending("indef", "nom", "pl") == ("e", "strong")  # ein has no plural
    assert signal_on("def", "dat", "m") == "determiner"
    assert signal_on("indef", "nom", "n") == "adjective"
    assert signal_on("none", "gen", "m") == "noun"


def test_adjective_stems():
    assert adjective_stem("hoch") == "hoh"
    assert adjective_stem("dunkel") == "dunkl"
    assert adjective_stem("teuer") == "teur"
    assert adjective_stem("sauer") == "saur"
    assert adjective_stem("leise") == "leis"
    assert adjective_stem("müde") == "müd"
    assert adjective_stem("klein") == "klein"
    assert adjective_stem("lila") is None
    assert adjective_stem("rosa") is None


@pytest.mark.parametrize(
    ("noun", "gender", "gen"),
    [
        ("Mann", "m", "Mannes"),
        ("Tag", "m", "Tages"),
        ("Haus", "n", "Hauses"),
        ("Tisch", "m", "Tisches"),
        ("Platz", "m", "Platzes"),
        ("Monat", "m", "Monats"),
        ("Abend", "m", "Abends"),
        ("Vater", "m", "Vaters"),
        ("Mädchen", "n", "Mädchens"),
        ("Auto", "n", "Autos"),
        ("Käse", "m", "Käses"),
        ("Kaffee", "m", "Kaffees"),
        ("Problem", "n", "Problems"),
        ("Zeugnis", "n", "Zeugnisses"),
        ("Bus", "m", "Busses"),
        ("Junge", "m", "Jungen"),
        ("Mensch", "m", "Menschen"),
        ("Student", "m", "Studenten"),
        ("Herr", "m", "Herrn"),
        ("Nachbar", "m", "Nachbarn"),
        ("Name", "m", "Namens"),
        ("Herz", "n", "Herzens"),
        ("Frau", "f", "Frau"),
    ],
)
def test_genitive_singular(noun, gender, gen):
    assert genitive_singular(noun, gender) == gen


def test_phrases_with_nouns():
    assert phrase("def", "dat", "m", "Junge", "klein").text == "dem kleinen Jungen"
    assert phrase("indef", "akk", "m", "Herr", "alt").text == "einen alten Herrn"
    assert phrase("def", "gen", "n", "Haus", "groß").text == "des großen Hauses"
    assert phrase("none", "gen", "m", "Kaffee", "heiß").text == "heißen Kaffees"
    assert (
        phrase("def", "dat", "pl", "Kind", "klein", plural="Kinder").text == "den kleinen Kindern"
    )
    assert phrase("def", "dat", "pl", "Auto", "rot", plural="Autos").text == "den roten Autos"
    assert phrase("poss", "nom", "f", "Katze", "lila").text == "meine lila Katze"
    assert phrase("indef", "nom", "n", "Haus", "hoch").text == "ein hohes Haus"
    assert phrase("def", "akk", "m", "Hund").text == "den Hund"
    p = phrase("indef", "dat", "f", "Frau", "nett")
    assert [(x.stem, x.ending, x.role) for x in p.parts] == [
        ("ein", "er", "determiner"),
        ("nett", "en", "adjective"),
        ("Frau", "", "noun"),
    ]
    assert p.kind == "mixed"
