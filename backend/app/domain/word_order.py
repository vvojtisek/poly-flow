"""Word order practice (Slovosled): put the shuffled words of a real sentence back in order. Pure.

The sentences are reviewed curriculum text (lesson scene lines, lexicon example sentences);
nothing is generated. The end punctuation is shown fixed; commas stay on their word. The first
word loses its capital when it is not a noun or a name (decided by the caller from the lexicon),
so the capital does not give the answer away.

Only the original order counts as matching. Some sentences allow another order (German "Heute
trinke ich Kaffee" / "Ich trinke heute Kaffee"); the UI says so and shows the original instead of
calling a different order wrong.
"""

import random
import re
from dataclasses import dataclass

MIN_TILES = 3
MAX_TILES = 10

_END = re.compile(r"[.!?…]+[\"“”»]?$")


@dataclass(frozen=True, slots=True)
class Puzzle:
    tiles: list[str]  # in the original order
    end: str  # the closing punctuation, shown fixed after the last tile


def split(sentence: str) -> Puzzle:
    text = " ".join(sentence.split())
    m = _END.search(text)
    end = m.group(0) if m else ""
    body = text[: m.start()].rstrip() if m else text
    return Puzzle(tiles=body.split(" ") if body else [], end=end)


def usable(p: Puzzle) -> bool:
    return MIN_TILES <= len(p.tiles) <= MAX_TILES and len(set(p.tiles)) > 1


# Pronoun and possessive forms a lexicon of dictionary forms may not list (euer, eure, unsere):
# a capital on these is only the sentence start.
# fmt: off
CLOSED_CLASS = {
    "de": {"euer", "eure", "euren", "eurem", "eurer", "unser", "unsere", "unseren", "unserem",
           "unserer", "meine", "meinen", "meinem", "meiner", "deine", "deinen", "deinem",
           "deiner", "seine", "seinen", "seinem", "seiner", "ihre", "ihren", "ihrem", "ihrer",
           "dieser", "diese", "dieses", "diesen", "diesem", "welche", "welcher", "welches",
           "jeder", "jede", "jedes", "man", "es", "wie", "wo", "was", "wer", "wann", "warum"},
    "fr": {"je", "tu", "il", "elle", "nous", "vous", "ils", "elles", "on", "le", "la", "les",
           "un", "une", "des", "mon", "ma", "mes", "ton", "ta", "tes", "son", "sa", "ses",
           "notre", "nos", "votre", "vos", "leur", "leurs", "ce", "cet", "cette", "ces"},
    "it": {"io", "tu", "lui", "lei", "noi", "voi", "loro", "il", "lo", "la", "i", "gli", "le",
           "un", "uno", "una", "mio", "mia", "miei", "mie", "tuo", "tua", "suo", "sua",
           "questo", "questa", "quello", "quella"},
    "en": {"you", "he", "she", "it", "we", "they", "the", "a", "an", "my", "your", "his", "her",
           "our", "their", "this", "that", "these", "those"},
}
# fmt: on


def lower_first(p: Puzzle) -> Puzzle:
    first = p.tiles[0]
    return Puzzle(tiles=[first[:1].lower() + first[1:], *p.tiles[1:]], end=p.end)


def shuffled(tiles: list[str], seed: str) -> list[str]:
    """A deterministic shuffle per sentence that differs from the original order."""
    rng = random.Random(seed)
    out = list(tiles)
    for _ in range(20):
        rng.shuffle(out)
        if out != tiles:
            return out
    return out[1:] + out[:1]


def marks(expected: list[str], given: list[str]) -> list[bool]:
    """Per position: is the right word there? Length mismatches count as wrong positions."""
    return [i < len(given) and given[i] == w for i, w in enumerate(expected)]


def same_words(expected: list[str], given: list[str]) -> bool:
    return sorted(expected) == sorted(given)
