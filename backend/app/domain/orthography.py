"""Language-specific spelling check for written answers (plan P2).

No global fuzzy threshold: each verdict names a concrete, explainable deviation.
"""

import re
import unicodedata
from dataclasses import dataclass
from enum import StrEnum

from app.domain.enums import Language


class Verdict(StrEnum):
    EXACT = "exact"
    VARIANT = "accepted_variant"  # e.g. ss for ß, oe for œ: correct, with a note
    CASE = "case"  # German noun not capitalised
    DIACRITICS = "diacritics"  # right letters, missing/wrong accents
    WRONG = "wrong"


@dataclass(frozen=True, slots=True)
class SpellingResult:
    verdict: Verdict
    score: float  # orthography measurement in [0, 1]
    note: str | None = None  # machine key for the UI explanation

    @property
    def correct(self) -> bool:
        """Counts as correct written production."""
        return self.verdict in (Verdict.EXACT, Verdict.VARIANT)


# Typographic apostrophe look-alikes -> ASCII apostrophe
_APOSTROPHES = str.maketrans({"\u2019": "'", "\u02bc": "'", "`": "'", "\u00b4": "'"})
_ARTICLES: dict[Language, tuple[str, ...]] = {
    Language.DE: ("der", "die", "das", "ein", "eine"),
    Language.FR: ("le", "la", "les", "l'", "un", "une"),
    Language.IT: ("il", "lo", "la", "i", "gli", "le", "l'", "un", "uno", "una", "un'"),
}
# Keyboard fallbacks that are accepted spellings, with the note shown to the learner.
_VARIANTS: dict[Language, tuple[tuple[str, str, str], ...]] = {
    Language.DE: (
        ("ß", "ss", "eszett_as_ss"),
        ("ä", "ae", "umlaut_as_e"),
        ("ö", "oe", "umlaut_as_e"),
        ("ü", "ue", "umlaut_as_e"),
        ("Ä", "Ae", "umlaut_as_e"),
        ("Ö", "Oe", "umlaut_as_e"),
        ("Ü", "Ue", "umlaut_as_e"),
    ),
    Language.FR: (("œ", "oe", "ligature_split"), ("æ", "ae", "ligature_split")),
    Language.IT: (),
}


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFC", text).translate(_APOSTROPHES)
    text = re.sub(r"\s+", " ", text).strip()
    return text.rstrip(".!?;:,").strip()


def _strip_article(language: Language, text: str) -> str:
    lowered = text.casefold()
    for art in sorted(_ARTICLES[language], key=len, reverse=True):
        if art.endswith("'"):
            if lowered.startswith(art) and len(text) > len(art):
                return text[len(art) :].lstrip()
        elif lowered.startswith(art + " "):
            return text[len(art) + 1 :]
    return text


def _fold_marks(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def check_spelling(language: Language, expected: str, answer: str, pos: str = "") -> SpellingResult:
    exp = normalize(expected)
    ans = normalize(answer)
    if not ans:
        return SpellingResult(Verdict.WRONG, 0.0)
    if _strip_article(language, exp) == exp:  # expected is a bare lemma: allow an article
        ans = _strip_article(language, ans)

    if ans == exp:
        return SpellingResult(Verdict.EXACT, 1.0)

    for original, fallback, note in _VARIANTS[language]:
        if original in exp and ans == exp.replace(original, fallback):
            return SpellingResult(Verdict.VARIANT, 0.9, note)
    # Several substitutions at once (e.g. "Strasse" for "Straße" with umlauts too)
    variant = exp
    notes = []
    for original, fallback, note in _VARIANTS[language]:
        if original in variant:
            variant = variant.replace(original, fallback)
            notes.append(note)
    if notes and ans == variant:
        return SpellingResult(Verdict.VARIANT, 0.9, notes[0])

    if ans.casefold() == exp.casefold():
        if language == Language.DE and pos.upper() in ("NOUN", "PROPN") and exp[:1].isupper():
            return SpellingResult(Verdict.CASE, 0.6, "de_noun_capital")
        return SpellingResult(Verdict.EXACT, 1.0)  # capitalisation is not significant here

    if _fold_marks(ans).casefold() == _fold_marks(exp).casefold():
        return SpellingResult(Verdict.DIACRITICS, 0.5, "diacritics")

    return SpellingResult(Verdict.WRONG, 0.0)
