import pytest

from app.domain.conjugation import PERSONS, conjugate, sentence_form

TABLE = {
    "sein": "bin bist ist sind seid sind",
    "haben": "habe hast hat haben habt haben",
    "können": "kann kannst kann können könnt können",
    "möchten": "möchte möchtest möchte möchten möchtet möchten",
    "wissen": "weiß weißt weiß wissen wisst wissen",
    "machen": "mache machst macht machen macht machen",
    "arbeiten": "arbeite arbeitest arbeitet arbeiten arbeitet arbeiten",
    "finden": "finde findest findet finden findet finden",
    "öffnen": "öffne öffnest öffnet öffnen öffnet öffnen",
    "zeichnen": "zeichne zeichnest zeichnet zeichnen zeichnet zeichnen",
    "rechnen": "rechne rechnest rechnet rechnen rechnet rechnen",
    "wohnen": "wohne wohnst wohnt wohnen wohnt wohnen",
    "atmen": "atme atmest atmet atmen atmet atmen",
    "lernen": "lerne lernst lernt lernen lernt lernen",
    "kommen": "komme kommst kommt kommen kommt kommen",
    "heißen": "heiße heißt heißt heißen heißt heißen",
    "tanzen": "tanze tanzt tanzt tanzen tanzt tanzen",
    "lächeln": "lächle lächelst lächelt lächeln lächelt lächeln",
    "erinnern": "erinnere erinnerst erinnert erinnern erinnert erinnern",
    "geben": "gebe gibst gibt geben gebt geben",
    "nehmen": "nehme nimmst nimmt nehmen nehmt nehmen",
    "essen": "esse isst isst essen esst essen",
    "lesen": "lese liest liest lesen lest lesen",
    "sehen": "sehe siehst sieht sehen seht sehen",
    "fahren": "fahre fährst fährt fahren fahrt fahren",
    "laufen": "laufe läufst läuft laufen lauft laufen",
    "halten": "halte hältst hält halten haltet halten",
    "lassen": "lasse lässt lässt lassen lasst lassen",
    "waschen": "wasche wäschst wäscht waschen wascht waschen",
    "wachsen": "wachse wächst wächst wachsen wachst wachsen",
    "vergessen": "vergesse vergisst vergisst vergessen vergesst vergessen",
    "empfehlen": "empfehle empfiehlst empfiehlt empfehlen empfehlt empfehlen",
    "gefallen": "gefalle gefällst gefällt gefallen gefallt gefallen",
    "unterhalten": "unterhalte unterhältst unterhält unterhalten unterhaltet unterhalten",
    "übersetzen": "übersetze übersetzt übersetzt übersetzen übersetzt übersetzen",
    "treffen": "treffe triffst trifft treffen trefft treffen",
    "beginnen": "beginne beginnst beginnt beginnen beginnt beginnen",
    "antworten": "antworte antwortest antwortet antworten antwortet antworten",
}


@pytest.mark.parametrize(("verb", "forms"), TABLE.items())
def test_present_tense(verb, forms):
    got = conjugate(verb)
    assert " ".join(got[p].text for p in PERSONS) == forms
    assert all(f.prefix is None for f in got.values())


@pytest.mark.parametrize(
    ("verb", "prefix", "du", "er"),
    [
        ("aufstehen", "auf", "stehst", "steht"),
        ("einladen", "ein", "lädst", "lädt"),
        ("anfangen", "an", "fängst", "fängt"),
        ("fernsehen", "fern", "siehst", "sieht"),
        ("wehtun", "weh", "tust", "tut"),
        ("vorbereiten", "vor", "bereitest", "bereitet"),
        ("kennenlernen", "kennen", "lernst", "lernt"),
    ],
)
def test_separable(verb, prefix, du, er):
    got = conjugate(verb)
    assert got["du"].prefix == prefix and got["du"].text == du and got["er"].text == er


def test_vowel_change_is_flagged_and_sentence_form():
    got = conjugate("fahren")
    assert got["du"].changed and not got["wir"].changed
    assert sentence_form(conjugate("aufstehen")["ich"], "ich") == "ich stehe … auf"
    assert sentence_form(got["er"], "er") == "er/sie/es fährt"


def test_features():
    from app.domain.conjugation import features

    assert features("sein") == ["irregular"]
    assert features("fahren") == ["vowel_change"]
    assert features("aufstehen") == ["separable"]
    assert features("arbeiten") == ["e_insertion"]
    assert features("heißen") == ["s_stem"]
    assert features("lächeln") == ["el_er"]
    assert features("einladen") == ["vowel_change", "separable", "e_insertion"]
