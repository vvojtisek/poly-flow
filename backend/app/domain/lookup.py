"""Tap a word in a text and find its dictionary entry: surface form → candidate lemmas.

Pure rules, no model. `candidates()` returns possible dictionary forms for one written word, most
likely first: the word itself, then a few irregular forms, then suffix stripping (plural, verb and
adjective endings). The caller looks the candidates up in the lexicon, so a wrong guess that is
not a real lemma costs nothing; a guess that is a real but different lemma is possible
(German "Weg" from "wegen"), which is why the UI shows the matched dictionary form, not only the
meaning.

German verbs are handled by the caller with a reverse index of the present-tense forms
(`app.domain.conjugation`), because the stem changes (gibt → geben) are not suffix rules.
"""

import re

from app.domain.enums import Language

MAX_WORD = 48

# Letters (any script the four languages use), with inner hyphens or apostrophes.
_WORD = re.compile(r"[^\W\d_]+(?:[-'\u2019][^\W\d_]+)*")

# Elided articles and pronouns: l'homme, j'ai, dell'acqua, un'amica.
_ELISION = re.compile(
    r"^(?:l|d|j|m|t|s|c|n|qu|jusqu|lorsqu|puisqu|dell|dall|nell|sull|all|un|quest|quell)['\u2019]",
    re.IGNORECASE,
)

# fmt: off
_IRREGULAR: dict[Language, dict[str, str]] = {
    "de": {
        "bin": "sein", "bist": "sein", "ist": "sein", "sind": "sein", "seid": "sein",
        "war": "sein", "warst": "sein", "waren": "sein", "wart": "sein", "gewesen": "sein",
        "hatte": "haben", "hattest": "haben", "hatten": "haben", "gehabt": "haben",
        "wurde": "werden", "wurden": "werden", "geworden": "werden",
        "dem": "der", "den": "der", "des": "der", "einem": "ein", "einen": "ein", "einer": "ein",
        "eines": "ein", "eine": "ein", "mir": "ich", "mich": "ich", "dir": "du", "dich": "du",
        "ihm": "er", "ihn": "er", "uns": "wir", "euch": "ihr", "ihnen": "sie",
    },
    "en": {
        "am": "be", "is": "be", "are": "be", "was": "be", "were": "be", "been": "be",
        "being": "be", "has": "have", "had": "have", "does": "do", "did": "do", "done": "do",
        "went": "go", "gone": "go", "said": "say", "made": "make", "got": "get", "took": "take",
        "taken": "take", "came": "come", "saw": "see", "seen": "see", "knew": "know",
        "known": "know", "thought": "think", "told": "tell", "gave": "give", "given": "give",
        "found": "find", "felt": "feel", "left": "leave", "kept": "keep", "brought": "bring",
        "bought": "buy", "began": "begin", "begun": "begin", "wrote": "write",
        "written": "write", "ran": "run", "ate": "eat", "eaten": "eat", "spoke": "speak",
        "spoken": "speak", "stood": "stand", "sat": "sit", "met": "meet", "paid": "pay",
        "heard": "hear", "held": "hold", "lost": "lose", "sent": "send", "built": "build",
        "children": "child", "men": "man", "women": "woman", "feet": "foot", "teeth": "tooth",
        "mice": "mouse", "better": "good", "best": "good", "worse": "bad", "worst": "bad",
        "me": "i", "him": "he", "her": "she", "us": "we", "them": "they",
    },
    "fr": {
        "suis": "être", "es": "être", "est": "être", "sommes": "être", "êtes": "être",
        "sont": "être", "était": "être", "été": "être", "ai": "avoir", "as": "avoir",
        "a": "avoir", "avons": "avoir", "avez": "avoir", "ont": "avoir", "avait": "avoir",
        "eu": "avoir", "vais": "aller", "vas": "aller", "va": "aller", "allons": "aller",
        "allez": "aller", "vont": "aller", "fais": "faire", "fait": "faire", "faisons": "faire",
        "faites": "faire", "font": "faire", "peux": "pouvoir", "peut": "pouvoir",
        "pouvons": "pouvoir", "pouvez": "pouvoir", "peuvent": "pouvoir", "veux": "vouloir",
        "veut": "vouloir", "voulons": "vouloir", "voulez": "vouloir", "veulent": "vouloir",
        "dois": "devoir", "doit": "devoir", "devons": "devoir", "devez": "devoir",
        "doivent": "devoir", "sais": "savoir", "sait": "savoir", "savons": "savoir",
        "savez": "savoir", "savent": "savoir", "dis": "dire", "dit": "dire", "disons": "dire",
        "dites": "dire", "disent": "dire", "la": "le", "les": "le", "une": "un", "des": "un",
        "belle": "beau", "bel": "beau", "nouvelle": "nouveau", "vieille": "vieux",
    },
    "it": {
        "sono": "essere", "sei": "essere", "è": "essere", "siamo": "essere", "siete": "essere",
        "era": "essere", "stato": "essere", "stata": "essere", "ho": "avere", "hai": "avere",
        "ha": "avere", "abbiamo": "avere", "avete": "avere", "hanno": "avere", "aveva": "avere",
        "vado": "andare", "vai": "andare", "va": "andare", "andiamo": "andare", "vanno": "andare",
        "faccio": "fare", "fai": "fare", "fa": "fare", "facciamo": "fare", "fanno": "fare",
        "posso": "potere", "puoi": "potere", "può": "potere", "possiamo": "potere",
        "possono": "potere", "voglio": "volere", "vuoi": "volere", "vuole": "volere",
        "vogliamo": "volere", "vogliono": "volere", "devo": "dovere", "devi": "dovere",
        "deve": "dovere", "dobbiamo": "dovere", "devono": "dovere", "so": "sapere",
        "sai": "sapere", "sa": "sapere", "sappiamo": "sapere", "sanno": "sapere",
        "dico": "dire", "dici": "dire", "dice": "dire", "diciamo": "dire", "dicono": "dire",
        "la": "il", "lo": "il", "i": "il", "gli": "il", "le": "il", "una": "uno", "un": "uno",
    },
}

# (suffix to strip, replacement), tried in order; only results of 2+ letters are kept.
_SUFFIXES: dict[Language, tuple[tuple[str, str], ...]] = {
    "de": (
        ("innen", "in"), ("nen", "n"), ("ern", ""), ("en", ""), ("en", "e"), ("er", ""),
        ("es", ""), ("em", ""), ("e", ""), ("n", ""), ("s", ""), ("st", "en"), ("t", "en"),
        ("e", "en"), ("est", "en"), ("et", "en"), ("te", "en"), ("ten", "en"), ("test", "en"),
        ("tet", "en"), ("st", "n"), ("t", "n"), ("e", "n"),
    ),
    "en": (
        ("ies", "y"), ("ied", "y"), ("ier", "y"), ("iest", "y"), ("ves", "f"), ("ves", "fe"),
        ("ses", "s"), ("xes", "x"), ("ches", "ch"), ("shes", "sh"), ("oes", "o"), ("s", ""),
        ("'s", ""), ("\u2019s", ""), ("ing", ""), ("ing", "e"), ("ed", ""), ("ed", "e"),
        ("d", ""), ("er", ""), ("est", ""), ("ly", ""), ("ily", "y"),
    ),
    "fr": (
        ("aux", "al"), ("eaux", "eau"), ("x", ""), ("s", ""), ("es", ""), ("e", ""),
        ("ée", "er"), ("ées", "er"), ("és", "er"), ("é", "er"), ("ons", "er"), ("ez", "er"),
        ("ent", "er"), ("es", "er"), ("e", "er"), ("ais", "er"), ("ait", "er"),
        ("aient", "er"), ("is", "ir"), ("it", "ir"), ("issons", "ir"), ("issez", "ir"),
        ("issent", "ir"), ("euse", "eux"), ("ive", "if"), ("ienne", "ien"), ("elle", "el"),
    ),
    "it": (
        ("i", "o"), ("i", "e"), ("e", "a"), ("a", "o"), ("he", "a"), ("hi", "o"),
        ("o", "are"), ("i", "are"), ("a", "are"), ("iamo", "are"), ("ate", "are"),
        ("ano", "are"), ("ato", "are"), ("o", "ere"), ("e", "ere"), ("ete", "ere"),
        ("ono", "ere"), ("uto", "ere"), ("o", "ire"), ("e", "ire"), ("ite", "ire"),
        ("ono", "ire"), ("ito", "ire"), ("isco", "ire"), ("isci", "ire"), ("isce", "ire"),
    ),
}
# fmt: on

_UMLAUT_BACK = str.maketrans({"ä": "a", "ö": "o", "ü": "u"})


def clean(word: str) -> str:
    """The first word in the tapped text, lowercased, with elided articles removed."""
    m = _WORD.search(word[: MAX_WORD * 2])
    if not m:
        return ""
    w = _ELISION.sub("", m.group(0)).replace("\u2019", "'")
    return w.lower()[:MAX_WORD]


def candidates(word: str, language: Language) -> list[str]:
    """Possible lemmas (lowercase), most likely first, without duplicates."""
    w = clean(word)
    if not w:
        return []
    out: list[str] = [w]
    irregular = _IRREGULAR.get(language, {}).get(w)
    if irregular:
        out.append(irregular)
    for suffix, repl in _SUFFIXES.get(language, ()):
        if w.endswith(suffix) and len(w) - len(suffix) >= 2:
            out.append(w[: -len(suffix)] + repl)
            # English doubled consonant: running → run, stopped → stop.
            if language == "en" and suffix in ("ing", "ed", "er", "est"):
                base = w[: -len(suffix)]
                if len(base) >= 3 and base[-1] == base[-2] and base[-1] not in "aeiouls":
                    out.append(base[:-1])
    if language == "de":
        # Umlaut plurals: Städte → Stadt, Äpfel → Apfel, Bücher → Buch.
        for c in list(out):
            back = c.translate(_UMLAUT_BACK)
            if back != c:
                out.append(back)
    seen: set[str] = set()
    return [c for c in out if len(c) >= 1 and not (c in seen or seen.add(c))]
