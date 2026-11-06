"""Noun gender from the ending: the reliable textbook rules, with how far each can be trusted.

Pure rules; no I/O. A rule either always holds ("always": no common exceptions) or usually
holds ("usually": a learner should expect exceptions). The hint is shown after a gender guess so
the learner sees a pattern, never as the source of the gender itself: the lexicon's gender is
authoritative, and when it disagrees with a rule the word is shown as an exception.
"""

from dataclasses import dataclass
from typing import Literal

from app.domain.enums import Language

Certainty = Literal["always", "usually"]


@dataclass(frozen=True, slots=True)
class Rule:
    suffix: str
    gender: str  # der/die/das for German, m/f for French and Italian
    certainty: Certainty
    min_length: int = 0  # the word must be longer than the suffix by at least this much


# Longest suffixes first, so the most specific rule wins. Rules too mixed to teach (French -eur,
# Italian -e or -ma) are left out rather than misteaching. Sources: standard learner grammars.
RULES: dict[Language, tuple[Rule, ...]] = {
    Language.DE: (
        Rule("schaft", "die", "always", 2),
        Rule("ismus", "der", "always", 2),
        Rule("chen", "das", "always", 2),
        Rule("lein", "das", "always", 2),
        Rule("heit", "die", "always", 2),
        Rule("keit", "die", "always", 2),
        Rule("ling", "der", "always", 2),
        Rule("ment", "das", "usually", 2),
        Rule("ung", "die", "always", 2),
        Rule("ion", "die", "always", 2),
        Rule("tät", "die", "always", 1),
        Rule("tum", "das", "usually", 2),
        Rule("ei", "die", "usually", 3),
        Rule("ik", "die", "usually", 3),
        Rule("ur", "die", "usually", 3),
        Rule("um", "das", "usually", 3),
        Rule("or", "der", "usually", 3),
        Rule("ig", "der", "usually", 2),
        Rule("e", "die", "usually", 3),
    ),
    Language.FR: (
        Rule("tion", "f", "always", 1),
        Rule("sion", "f", "always", 1),
        Rule("ment", "m", "usually", 2),
        Rule("isme", "m", "always", 1),
        Rule("ette", "f", "always", 1),
        Rule("eau", "m", "usually", 1),
        Rule("age", "m", "usually", 2),
        Rule("ure", "f", "usually", 2),
        Rule("té", "f", "usually", 2),
    ),
    Language.IT: (
        Rule("zione", "f", "always", 1),
        Rule("sione", "f", "always", 1),
        Rule("tà", "f", "always", 1),
        Rule("tù", "f", "always", 1),
        Rule("ore", "m", "usually", 2),
        Rule("o", "m", "usually", 2),
        Rule("a", "f", "usually", 2),
    ),
}


@dataclass(frozen=True, slots=True)
class Hint:
    suffix: str
    gender: str
    certainty: Certainty
    exception: bool  # the word's real gender differs from the rule's


def hint(language: Language, lemma: str, gender: str | None) -> Hint | None:
    """The first rule matching the lemma's ending, or None when no rule applies."""
    word = lemma.lower()
    for rule in RULES.get(language, ()):
        if word.endswith(rule.suffix) and len(word) >= len(rule.suffix) + rule.min_length:
            return Hint(
                rule.suffix,
                rule.gender,
                rule.certainty,
                gender is not None and gender != rule.gender,
            )
    return None


GENDERS: dict[Language, tuple[str, ...]] = {
    Language.DE: ("der", "die", "das"),
    Language.FR: ("m", "f"),
    Language.IT: ("m", "f"),
}


def normalise(language: Language, gender: str | None) -> str | None:
    """The lexicon gender as one of GENDERS[language]; None for "m/f" and unknown values."""
    if gender is None:
        return None
    g = gender.strip().lower()
    return g if g in GENDERS.get(language, ()) else None
