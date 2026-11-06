import pytest

from app.domain.conjugation_romance import conjugate_fr, conjugate_it, features


def fr(verb: str) -> list[str]:
    return [f"{f.pronoun} {f.stem}{f.ending}".replace("' ", "'") for f in conjugate_fr(verb)]


def it(verb: str) -> list[str]:
    return [f.stem + f.ending for f in conjugate_it(verb)]


@pytest.mark.parametrize(
    ("verb", "forms"),
    [
        ("parler", ["je parle", "tu parles", "il/elle parle", "nous parlons", "vous parlez",
                    "ils/elles parlent"]),
        ("aimer", ["j'aime", "tu aimes", "il/elle aime", "nous aimons", "vous aimez",
                   "ils/elles aiment"]),
        ("manger", ["je mange", "tu manges", "il/elle mange", "nous mangeons", "vous mangez",
                    "ils/elles mangent"]),
        ("commencer", ["je commence", "tu commences", "il/elle commence", "nous commençons",
                       "vous commencez", "ils/elles commencent"]),
        ("appeler", ["j'appelle", "tu appelles", "il/elle appelle", "nous appelons",
                     "vous appelez", "ils/elles appellent"]),
        ("acheter", ["j'achète", "tu achètes", "il/elle achète", "nous achetons",
                     "vous achetez", "ils/elles achètent"]),
        ("préférer", ["je préfère", "tu préfères", "il/elle préfère", "nous préférons",
                      "vous préférez", "ils/elles préfèrent"]),
        ("payer", ["je paie", "tu paies", "il/elle paie", "nous payons", "vous payez",
                   "ils/elles paient"]),
        ("finir", ["je finis", "tu finis", "il/elle finit", "nous finissons", "vous finissez",
                   "ils/elles finissent"]),
        ("partir", ["je pars", "tu pars", "il/elle part", "nous partons", "vous partez",
                    "ils/elles partent"]),
        ("dormir", ["je dors", "tu dors", "il/elle dort", "nous dormons", "vous dormez",
                    "ils/elles dorment"]),
        ("ouvrir", ["j'ouvre", "tu ouvres", "il/elle ouvre", "nous ouvrons", "vous ouvrez",
                    "ils/elles ouvrent"]),
        ("vendre", ["je vends", "tu vends", "il/elle vend", "nous vendons", "vous vendez",
                    "ils/elles vendent"]),
        ("conduire", ["je conduis", "tu conduis", "il/elle conduit", "nous conduisons",
                      "vous conduisez", "ils/elles conduisent"]),
        ("comprendre", ["je comprends", "tu comprends", "il/elle comprend", "nous comprenons",
                        "vous comprenez", "ils/elles comprennent"]),
        ("apprendre", ["j'apprends", "tu apprends", "il/elle apprend", "nous apprenons",
                       "vous apprenez", "ils/elles apprennent"]),
        ("être", ["je suis", "tu es", "il/elle est", "nous sommes", "vous êtes",
                  "ils/elles sont"]),
        ("avoir", ["j'ai", "tu as", "il/elle a", "nous avons", "vous avez", "ils/elles ont"]),
        ("habiter", ["j'habite", "tu habites", "il/elle habite", "nous habitons",
                     "vous habitez", "ils/elles habitent"]),
    ],
)  # fmt: skip
def test_french(verb: str, forms: list[str]) -> None:
    assert fr(verb) == forms


def test_french_regular_e_acute_not_in_last_syllable_is_kept() -> None:
    # réparer: the é is not in the stressed syllable, so no è.
    assert fr("réparer")[0] == "je répare"
    assert fr("répéter")[0] == "je répète"


@pytest.mark.parametrize(
    ("verb", "forms"),
    [
        ("parlare", ["parlo", "parli", "parla", "parliamo", "parlate", "parlano"]),
        ("cercare", ["cerco", "cerchi", "cerca", "cerchiamo", "cercate", "cercano"]),
        ("pagare", ["pago", "paghi", "paga", "paghiamo", "pagate", "pagano"]),
        ("mangiare", ["mangio", "mangi", "mangia", "mangiamo", "mangiate", "mangiano"]),
        ("studiare", ["studio", "studi", "studia", "studiamo", "studiate", "studiano"]),
        ("inviare", ["invio", "invii", "invia", "inviamo", "inviate", "inviano"]),
        ("prendere", ["prendo", "prendi", "prende", "prendiamo", "prendete", "prendono"]),
        ("dormire", ["dormo", "dormi", "dorme", "dormiamo", "dormite", "dormono"]),
        ("finire", ["finisco", "finisci", "finisce", "finiamo", "finite", "finiscono"]),
        ("essere", ["sono", "sei", "è", "siamo", "siete", "sono"]),
        ("fare", ["faccio", "fai", "fa", "facciamo", "fate", "fanno"]),
        ("ottenere", ["ottengo", "ottieni", "ottiene", "otteniamo", "ottenete", "ottengono"]),
    ],
)
def test_italian(verb: str, forms: list[str]) -> None:
    assert it(verb) == forms


def test_stressed_i_keeps_two_in_tu_only() -> None:
    assert it("inviare")[1] == "invii"
    assert it("studiare")[1] == "studi"
    assert it("inviare")[3] == "inviamo"


def test_changed_marks_only_what_differs() -> None:
    assert [f.changed for f in conjugate_fr("manger")] == [False, False, False, True, False, False]
    assert all(f.changed for f in conjugate_fr("être"))
    assert not any(f.changed for f in conjugate_fr("parler"))
    assert [f.changed for f in conjugate_it("cercare")] == [False, True, False, True, False, False]


def test_features() -> None:
    assert features("parler", "fr") == ["fr_er"]
    assert features("acheter", "fr") == ["fr_er", "spelling", "elision"]
    assert features("finir", "fr") == ["fr_ir"]
    assert features("partir", "fr") == ["fr_partir"]
    assert features("ouvrir", "fr") == ["fr_ouvrir", "elision"]
    assert features("vendre", "fr") == ["fr_re"]
    assert features("conduire", "fr") == ["fr_uire"]
    assert features("être", "fr") == ["irregular"]
    assert features("parlare", "it") == ["it_are"]
    assert features("cercare", "it") == ["it_are", "it_h"]
    assert features("mangiare", "it") == ["it_are", "it_i"]
    assert features("finire", "it") == ["it_isc"]
    assert features("prendere", "it") == ["it_ere"]
    assert features("andare", "it") == ["irregular"]


@pytest.mark.parametrize("verb", ["", "chat", "xyz"])
def test_not_a_verb(verb: str) -> None:
    with pytest.raises(ValueError):
        conjugate_fr(verb)
    with pytest.raises(ValueError):
        conjugate_it(verb)
