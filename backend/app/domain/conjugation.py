"""German present tense (Präsens): rules plus the irregular verbs, as stem + ending. Pure rules.

Regular: stem = infinitive minus -en/-n, endings -e, -st, -t, -en, -t, -en, with the standard
adjustments: an -e- before -st/-t after a stem in -t/-d or consonant + m/n (arbeitest, öffnet);
only -t for du after s, ß, x, z (heißt); verbs in -eln/-ern take -n for wir/sie and lose the
stem e for ich in -eln (ich lächle).

Irregular: sein, haben, werden, wissen, tun, the modal verbs and möchten are listed whole;
strong verbs with a vowel change in du and er/sie/es (geben → gibst, fahren → fährst,
laufen → läufst) are listed by their base verb and found through prefixes (vergessen, einladen,
fernsehen). Separable prefixes are split off and returned separately (ich stehe ... auf).

A verb not in the lists is treated as regular in the present tense. The lists cover the common
strong verbs; a rare strong verb missing from them would be shown with regular forms, which is
why the UI says the forms are built by rules.
"""

from dataclasses import dataclass
from typing import Literal

Person = Literal["ich", "du", "er", "wir", "ihr", "sie"]
PERSONS: tuple[Person, ...] = ("ich", "du", "er", "wir", "ihr", "sie")

# fmt: off
_WHOLE: dict[str, tuple[str, str, str, str, str, str]] = {
    "sein": ("bin", "bist", "ist", "sind", "seid", "sind"),
    "haben": ("habe", "hast", "hat", "haben", "habt", "haben"),
    "werden": ("werde", "wirst", "wird", "werden", "werdet", "werden"),
    "wissen": ("weiß", "weißt", "weiß", "wissen", "wisst", "wissen"),
    "tun": ("tue", "tust", "tut", "tun", "tut", "tun"),
    "können": ("kann", "kannst", "kann", "können", "könnt", "können"),
    "müssen": ("muss", "musst", "muss", "müssen", "müsst", "müssen"),
    "dürfen": ("darf", "darfst", "darf", "dürfen", "dürft", "dürfen"),
    "wollen": ("will", "willst", "will", "wollen", "wollt", "wollen"),
    "sollen": ("soll", "sollst", "soll", "sollen", "sollt", "sollen"),
    "mögen": ("mag", "magst", "mag", "mögen", "mögt", "mögen"),
    "möchten": ("möchte", "möchtest", "möchte", "möchten", "möchtet", "möchten"),
}

# Strong verbs: the stem used for du and er/sie/es.
_CHANGED: dict[str, str] = {
    # e → i / ie
    "geben": "gib", "nehmen": "nimm", "sprechen": "sprich", "essen": "iss", "helfen": "hilf",
    "treffen": "triff", "vergessen": "vergiss", "sterben": "stirb", "werfen": "wirf",
    "brechen": "brich", "messen": "miss", "fressen": "friss", "gelten": "gilt", "treten": "tritt",
    "stechen": "stich", "verderben": "verdirb", "werben": "wirb", "bergen": "birg",
    "sehen": "sieh", "lesen": "lies", "empfehlen": "empfiehl", "befehlen": "befiehl",
    "stehlen": "stiehl", "geschehen": "geschieh",
    # a → ä, au → äu, o → ö
    "fahren": "fähr", "schlafen": "schläf", "tragen": "träg", "fallen": "fäll",
    "fangen": "fäng", "halten": "hält", "lassen": "läss", "waschen": "wäsch",
    "wachsen": "wächs", "laden": "läd", "raten": "rät", "schlagen": "schläg", "graben": "gräb",
    "braten": "brät", "blasen": "bläs", "backen": "bäck", "laufen": "läuf", "saufen": "säuf",
    "stoßen": "stöß",
}
# fmt: on

# Separable prefixes (stressed); longest first. Inseparable ones (be-, er-, ver-, über- in
# übersetzen ...) stay on the verb.
_SEPARABLE = (
    "zurück", "weiter", "kennen", "spazieren", "zusammen", "fern", "nach", "auf", "aus", "ein",
    "mit", "vor", "weg", "her", "hin", "los", "an", "ab", "zu", "um", "weh", "dar", "bei", "fest",
)  # fmt: skip
_INSEPARABLE = (
    "be",
    "ge",
    "er",
    "ver",
    "zer",
    "ent",
    "emp",
    "miss",
    "über",
    "unter",
    "wider",
    "hinter",
)
# Verbs that look like prefix + verb but are not separable in their usual sense.
_NOT_SPLIT = {"übersetzen", "überlegen", "überraschen", "unterhalten", "unterschreiben",
              "wiederholen", "umarmen", "antworten", "einigen"}  # fmt: skip


@dataclass(frozen=True, slots=True)
class Form:
    stem: str  # what comes before the ending (with any vowel change)
    ending: str  # the person ending ("" for ich kann)
    changed: bool  # the stem vowel changed (strong verb) or the form is irregular
    prefix: str | None  # separable prefix, placed at the end of the clause

    @property
    def text(self) -> str:
        return self.stem + self.ending


def split_prefix(verb: str) -> tuple[str | None, str]:
    """(separable prefix, base verb). Only splits when the rest is itself a verb-like word."""
    if verb in _NOT_SPLIT:
        return None, verb
    for p in _SEPARABLE:
        rest = verb[len(p) :]
        if verb.startswith(p) and len(rest) >= 3 and rest.endswith("n"):
            return p, rest
    return None, verb


def _base_lookup(verb: str) -> tuple[str, str]:
    """(inseparable prefix, base) for finding a strong verb inside vergessen, empfehlen ..."""
    if verb in _WHOLE or verb in _CHANGED:
        return "", verb
    for p in _INSEPARABLE:
        rest = verb[len(p) :]
        if verb.startswith(p) and (rest in _CHANGED or rest in _WHOLE):
            return p, rest
    return "", verb


def _stem(verb: str) -> str:
    if verb.endswith(("eln", "ern")):
        return verb[:-1]
    if verb.endswith("en"):
        return verb[:-2]
    if verb.endswith("n"):
        return verb[:-1]
    return verb


def _needs_e(stem: str) -> bool:
    """arbeit-e-st, öffn-e-t: a stem in -t/-d, or consonant + m/n (not after l, r, h, m, n)."""
    if stem.endswith(("t", "d")):
        return True
    if len(stem) >= 2 and stem[-1] in "mn":
        before = stem[-2]
        if before in "aeiouäöülrmn":
            return False
        # h after a vowel only lengthens it (wohn-st); in ch it is a consonant (rechn-e-st).
        return not (before == "h" and stem[-3:-2] != "c")
    return False


def _hissing(stem: str) -> bool:
    return stem.endswith(("s", "ß", "x", "z"))


def conjugate(infinitive: str) -> dict[Person, Form]:
    """Present tense of a German verb (infinitive as in the lexicon, e.g. "aufstehen")."""
    verb = infinitive.strip().lower()
    prefix, rest = split_prefix(verb)
    insep, base = _base_lookup(rest)
    if base in _WHOLE:
        forms = _WHOLE[base]
        return {p: Form(insep + f, "", True, prefix) for p, f in zip(PERSONS, forms, strict=True)}
    stem = insep + _stem(base)
    changed = insep + _CHANGED[base] if base in _CHANGED else None
    el = base.endswith("eln")
    er = base.endswith("ern")
    plural_end = "n" if (el or er) else "en"
    e = _needs_e(stem)
    out: dict[Person, Form] = {}
    out["ich"] = Form(stem[:-2] + "l" if el else stem, "e", False, prefix)
    if changed:
        # Strong verbs: no -e- insertion; a changed stem in -t takes no extra -t (er hält).
        du_end = "t" if _hissing(changed) else "st"
        er_end = "" if changed.endswith("t") else "t"
        out["du"] = Form(changed, du_end, True, prefix)
        out["er"] = Form(changed, er_end, True, prefix)
    else:
        out["du"] = Form(stem, "est" if e else ("t" if _hissing(stem) else "st"), False, prefix)
        out["er"] = Form(stem, "et" if e else "t", False, prefix)
    out["wir"] = Form(stem, plural_end, False, prefix)
    out["ihr"] = Form(stem, "et" if e else "t", False, prefix)
    out["sie"] = Form(stem, plural_end, False, prefix)
    return out


def sentence_form(form: Form, person: Person) -> str:
    """ "ich stehe ... auf" for a separable verb, else "ich stehe"."""
    pronoun = "er/sie/es" if person == "er" else "sie/Sie" if person == "sie" else person
    if form.prefix:
        return f"{pronoun} {form.text} … {form.prefix}"
    return f"{pronoun} {form.text}"


Feature = Literal["irregular", "vowel_change", "separable", "e_insertion", "s_stem", "el_er"]


def features(infinitive: str) -> list[Feature]:
    """What is special about this verb in the present tense, for the explanation in the UI."""
    forms = conjugate(infinitive)
    verb = infinitive.strip().lower()
    _, rest = split_prefix(verb)
    _, base = _base_lookup(rest)
    out: list[Feature] = []
    if base in _WHOLE:
        out.append("irregular")
    elif base in _CHANGED:
        out.append("vowel_change")
    if forms["du"].prefix:
        out.append("separable")
    if base not in _WHOLE:
        if forms["ihr"].ending == "et":
            out.append("e_insertion")
        if base not in _CHANGED and forms["du"].ending == "t":
            out.append("s_stem")
        if base.endswith(("eln", "ern")):
            out.append("el_er")
    return out
