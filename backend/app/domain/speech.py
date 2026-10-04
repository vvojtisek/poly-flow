"""Does a transcript of the learner's speech say the expected word? (policy v3)

This judges the *transcript*, not pronunciation: Whisper's word probability is how sure the
model is of its own transcription, not a calibrated pronunciation score (see phonetic_score).
A spoken answer can only confirm production. A transcript that does not match, or that the
model is unsure of, never counts against the learner: speech recognition fails for reasons
(a quiet microphone, a child's voice, background noise) that say nothing about knowledge.
"""

import re
import unicodedata
from dataclasses import dataclass

from app.domain.enums import Language
from app.domain.orthography import ARTICLES


@dataclass(frozen=True, slots=True)
class SpokenWord:
    word: str
    probability: float


@dataclass(frozen=True, slots=True)
class SpokenVerdict:
    matched: bool  # the transcript says the expected word (and nothing else)
    confidence: float | None  # lowest probability of the matched words; None if no match


def _tokens(text: str) -> list[str]:
    text = unicodedata.normalize("NFC", text).replace("\u2019", "'").casefold()
    return re.findall(r"[\w']+", text)


def _strip_articles(language: Language, tokens: list[str]) -> list[str]:
    articles = {a.rstrip("'") for a in ARTICLES[language]}
    out = []
    for t in tokens:
        head, _, rest = t.partition("'")  # l'école -> école, un'amica -> amica
        if rest and head + "'" in ARTICLES[language]:
            t = rest
        elif t in articles:
            continue
        out.append(t)
    return out


def judge(language: Language, lemma: str, words: list[SpokenWord]) -> SpokenVerdict:
    """Match when the transcript, articles aside, is exactly the lemma's words.

    casefold() maps ß to ss, so "Straße" and a transcribed "Strasse" agree. Extra words do not
    match: saying several guesses at once must not pass.
    """
    spoken = [(token, w.probability) for w in words for token in _tokens(w.word)]
    expected = _strip_articles(language, _tokens(lemma))
    if expected:
        spoken = [(s, p) for t, p in spoken for s in _strip_articles(language, [t])]
    else:  # the word is itself an article (der, the, la): compare as said
        expected = _tokens(lemma)
    if not expected or [t for t, _ in spoken] != expected:
        return SpokenVerdict(matched=False, confidence=None)
    return SpokenVerdict(matched=True, confidence=min(p for _, p in spoken))
