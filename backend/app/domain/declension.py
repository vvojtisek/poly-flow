"""German noun phrase declension: determiner, adjective, noun. Pure rules; no I/O.

Covers the standard paradigm taught at A1-B1: four cases, three genders and the plural, with the
definite article (der), the indefinite article (ein), kein, the possessive mein (as the model for
dein/sein/ihr/unser/euer), and no determiner (strong adjective endings).

The core teaching idea, which the UI visualises, is the *signal*: the case/gender ending
(r, e, s, m, n) appears once. If the determiner carries it, the adjective takes a weak ending
(-e or -en); if the determiner has no ending (ein, kein, mein in three cells) or there is no
determiner, the adjective carries the signal itself (strong ending).

Nouns: feminine nouns never change in the singular; masculine and neuter nouns add -(e)s in the
genitive; weak masculine nouns (n-declension) add -(e)n outside the nominative; the dative plural
adds -n. Adjectival nouns (der Erwachsene) are excluded because they decline like adjectives.
"""

from dataclasses import dataclass
from typing import Literal

Case = Literal["nom", "akk", "dat", "gen"]
Gender = Literal["m", "f", "n", "pl"]
Det = Literal["def", "indef", "kein", "poss", "none"]

CASES: tuple[Case, ...] = ("nom", "akk", "dat", "gen")
GENDERS: tuple[Gender, ...] = ("m", "f", "n", "pl")
DETS: tuple[Det, ...] = ("def", "indef", "kein", "poss", "none")
ARTICLE_GENDER = {"der": "m", "die": "f", "das": "n"}

# Definite article (der-words); the ending after "d" is the signal.
_DEF = {
    "nom": {"m": "der", "f": "die", "n": "das", "pl": "die"},
    "akk": {"m": "den", "f": "die", "n": "das", "pl": "die"},
    "dat": {"m": "dem", "f": "der", "n": "dem", "pl": "den"},
    "gen": {"m": "des", "f": "der", "n": "des", "pl": "der"},
}
# Endings of ein-words (ein, kein, mein); "" = no ending, None = no form (ein has no plural).
_EIN_END = {
    "nom": {"m": "", "f": "e", "n": "", "pl": "e"},
    "akk": {"m": "en", "f": "e", "n": "", "pl": "e"},
    "dat": {"m": "em", "f": "er", "n": "em", "pl": "en"},
    "gen": {"m": "es", "f": "er", "n": "es", "pl": "er"},
}
# Strong adjective endings (no determiner): the adjective carries the signal, except the
# masculine/neuter genitive, where the noun's -(e)s already marks the case.
_STRONG = {
    "nom": {"m": "er", "f": "e", "n": "es", "pl": "e"},
    "akk": {"m": "en", "f": "e", "n": "es", "pl": "e"},
    "dat": {"m": "em", "f": "er", "n": "em", "pl": "en"},
    "gen": {"m": "en", "f": "er", "n": "en", "pl": "er"},
}
_STEM = {"indef": "ein", "kein": "kein", "poss": "mein"}

Kind = Literal["weak", "mixed", "strong"]


@dataclass(frozen=True, slots=True)
class Determiner:
    stem: str  # "d" for der/die/das, "ein", "kein", "mein"; "" when there is none
    ending: str  # the part that carries case and gender ("er", "en", "" ...)

    @property
    def text(self) -> str:
        return self.stem + self.ending


def determiner(det: Det, case: Case, gender: Gender) -> Determiner | None:
    """The determiner form, split into stem and ending; None when it does not exist."""
    if det == "none":
        return None
    if det == "def":
        form = _DEF[case][gender]
        return Determiner(form[0], form[1:])
    if det == "indef" and gender == "pl":
        return None  # "ein" has no plural: the phrase goes strong (kleine Kinder)
    return Determiner(_STEM[det], _EIN_END[case][gender])


def adjective_ending(det: Det, case: Case, gender: Gender) -> tuple[str, Kind]:
    """Adjective ending and the declension type that produces it."""
    d = determiner(det, case, gender)
    if d is None:
        return _STRONG[case][gender], "strong"
    if det == "def":
        weak_e = (case == "nom" and gender != "pl") or (case == "akk" and gender in ("f", "n"))
        return ("e" if weak_e else "en"), "weak"
    if d.ending == "":
        # ein/kein/mein without an ending: the adjective takes the article's missing signal.
        return _STRONG[case][gender], "mixed"
    weak_e = case in ("nom", "akk") and gender == "f"
    return ("e" if weak_e else "en"), "mixed"


def signal_on(det: Det, case: Case, gender: Gender) -> Literal["determiner", "adjective", "noun"]:
    """Which word carries the case/gender signal in this cell."""
    d = determiner(det, case, gender)
    if d is not None and d.ending:
        return "determiner"
    if case == "gen" and gender in ("m", "n"):
        return "noun"
    return "adjective"


# ---------------------------------------------------------------- adjectives

_INDECLINABLE = frozenset({"rosa", "lila", "super", "prima", "orange", "beige", "extra"})


def adjective_stem(lemma: str) -> str | None:
    """Stem taking the ending (hoch → hoh, dunkel → dunkl, teuer → teur); None if indeclinable."""
    w = lemma.strip()
    if not w or w.lower() in _INDECLINABLE:
        return None
    if w == "hoch":
        return "hoh"
    if w.endswith("el"):
        return w[:-2] + "l"
    if w.endswith(("euer", "auer")):
        return w[:-2] + "r"
    if w.endswith("e"):
        return w[:-1]
    return w


# ---------------------------------------------------------------- nouns

# fmt: off
# Weak masculine nouns (n-declension). Listed, not guessed: a heuristic would misteach Käse or See.
_N_DECL = frozenset(
    {
        "Junge", "Kollege", "Kunde", "Hase", "Löwe", "Affe", "Neffe", "Franzose", "Russe", "Pole",
        "Grieche", "Türke", "Schwede", "Riese", "Bote", "Zeuge", "Experte", "Laie", "Rabe",
        "Student", "Präsident", "Assistent", "Patient", "Elefant", "Lieferant", "Praktikant",
        "Polizist", "Tourist", "Journalist", "Pianist", "Komponist", "Spezialist",
        "Soldat", "Kandidat", "Automat", "Planet", "Pilot", "Fotograf", "Biologe", "Psychologe",
        "Mensch", "Herr", "Nachbar", "Bauer", "Held", "Prinz", "Bär", "Graf", "Kamerad",
        "Fürst", "Narr", "Christ",
    }
)
# n-declension nouns that also take -s in the genitive (des Namens).
# fmt: on
_N_DECL_GEN_S = frozenset(
    {"Name", "Buchstabe", "Gedanke", "Glaube", "Wille", "Friede", "Funke", "Same"}
)
_ADJECTIVAL = frozenset(
    {"Erwachsene", "Deutsche", "Bekannte", "Verwandte", "Angestellte", "Beamte"}
)
PLURAL_ONLY = frozenset({"Eltern", "Leute", "Geschwister", "Ferien", "Kosten", "Lebensmittel"})
# Genitive singular forms that no simple rule produces.
_GEN_SPECIAL = {"Bus": "Busses", "Herz": "Herzens"}

_VOWELS = ("äu", "au", "ei", "eu", "ie", "ai", "a", "e", "i", "o", "u", "ä", "ö", "ü", "y")


def _syllables(word: str) -> int:
    w, n, i = word.lower(), 0, 0
    while i < len(w):
        for v in _VOWELS:
            if w.startswith(v, i):
                n += 1
                i += len(v)
                while i < len(w) and w[i] in "aeiouäöüy":
                    i += 1
                break
        else:
            i += 1
    return n


def declinable_noun(lemma: str) -> bool:
    return lemma not in _ADJECTIVAL


def is_n_declension(lemma: str) -> bool:
    return lemma in _N_DECL or lemma in _N_DECL_GEN_S


def _n_ending(lemma: str) -> str:
    """-n after -e, -er and -ar (Junge, Bauer, Nachbar, Herr), otherwise -en (Mensch, Student)."""
    return "n" if lemma.endswith(("e", "er", "ar")) or lemma == "Herr" else "en"


def genitive_singular(lemma: str, gender: Gender) -> str:
    """Genitive singular of a masculine/neuter/feminine noun (feminine is unchanged)."""
    if gender == "f":
        return lemma
    if lemma in _GEN_SPECIAL:
        return _GEN_SPECIAL[lemma]
    if lemma in _N_DECL_GEN_S:
        return lemma + "ns"
    if lemma in _N_DECL:
        return lemma + _n_ending(lemma)
    low = lemma.lower()
    if low.endswith("nis"):
        return lemma + "ses"
    if low.endswith(("s", "ß", "x", "z", "sch")):
        return lemma + "es"
    if low.endswith(("e", "el", "en", "er", "em", "chen", "lein", "a", "i", "o", "u", "y")):
        return lemma + "s"
    # Short words prefer -es (des Mannes, des Tages), longer ones -s (des Monats, des Abends).
    return lemma + ("es" if _syllables(lemma) == 1 else "s")


def noun_form(lemma: str, gender: Gender, case: Case, plural: str | None = None) -> tuple[str, str]:
    """(stem, ending) of the noun in this case; the ending is what declension added."""
    if gender == "pl":
        form = plural or lemma
        if case == "dat" and not form.endswith(("n", "s")):
            return form, "n"
        return form, ""
    if gender == "f" or case == "nom":
        return lemma, ""
    if case == "gen":
        g = genitive_singular(lemma, gender)
        return lemma, g[len(lemma) :] if g.startswith(lemma) else g
    if is_n_declension(lemma):
        return lemma, _n_ending(lemma)
    if lemma == "Herz" and case == "dat":
        return lemma, "en"
    return lemma, ""


# fmt: off
# Plurals of frequent nouns, so the builder can show the plural with a real noun.
PLURALS = {
    "Kind": "Kinder", "Mann": "Männer", "Frau": "Frauen", "Tag": "Tage", "Haus": "Häuser",
    "Freund": "Freunde", "Freundin": "Freundinnen", "Buch": "Bücher", "Hund": "Hunde",
    "Katze": "Katzen", "Stadt": "Städte", "Land": "Länder", "Jahr": "Jahre", "Frage": "Fragen",
    "Schule": "Schulen", "Auto": "Autos", "Tisch": "Tische", "Stuhl": "Stühle", "Baum": "Bäume",
    "Blume": "Blumen", "Apfel": "Äpfel", "Vogel": "Vögel", "Lehrer": "Lehrer", "Zimmer": "Zimmer",
    "Fenster": "Fenster", "Tür": "Türen", "Bruder": "Brüder", "Schwester": "Schwestern",
    "Sohn": "Söhne", "Tochter": "Töchter", "Mutter": "Mütter", "Vater": "Väter",
    "Mädchen": "Mädchen", "Junge": "Jungen", "Student": "Studenten", "Mensch": "Menschen",
    "Herr": "Herren", "Woche": "Wochen", "Stunde": "Stunden", "Monat": "Monate", "Tier": "Tiere",
    "Straße": "Straßen", "Hand": "Hände", "Kopf": "Köpfe", "Bett": "Betten", "Ei": "Eier",
    "Farbe": "Farben", "Problem": "Probleme", "Name": "Namen", "Pferd": "Pferde",
}
# fmt: on


@dataclass(frozen=True, slots=True)
class Part:
    stem: str
    ending: str
    role: Literal["determiner", "adjective", "noun"]


@dataclass(frozen=True, slots=True)
class Phrase:
    parts: tuple[Part, ...]
    kind: Kind  # weak, mixed or strong adjective declension
    signal: Literal["determiner", "adjective", "noun"]

    @property
    def text(self) -> str:
        return " ".join(p.stem + p.ending for p in self.parts)


def phrase(
    det: Det,
    case: Case,
    gender: Gender,
    noun: str,
    adjective: str | None = None,
    plural: str | None = None,
) -> Phrase:
    """Build the noun phrase; the noun's own gender is the caller's to supply ("pl" for plural)."""
    parts: list[Part] = []
    d = determiner(det, case, gender)
    if d is not None:
        parts.append(Part(d.stem, d.ending, "determiner"))
    ending, kind = adjective_ending(det, case, gender)
    stem = adjective_stem(adjective) if adjective else None
    if adjective and stem is None:
        parts.append(Part(adjective, "", "adjective"))  # lila, rosa: no ending
    elif stem is not None:
        parts.append(Part(stem, ending, "adjective"))
    n_stem, n_end = noun_form(noun, gender, case, plural)
    parts.append(Part(n_stem, n_end, "noun"))
    return Phrase(tuple(parts), kind, signal_on(det, case, gender))
