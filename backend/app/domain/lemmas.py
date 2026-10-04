"""Frequency lemma lists: the format rules shared by the build script, importer and schema.

A frequency lemma is a lowercase ASCII dictionary form ranked by corpus frequency. It is a
reference list, not curriculum: it has no Czech gloss, so lessons and checks never draw from
it directly (see data/README.md, "Frequency lemmas").
"""

import re

# Lowercase ASCII letters; a hyphen only between letters (compounds such as "well-known").
LEMMA_PATTERN = r"^[a-z]+(-[a-z]+)*$"
LOCALE_PATTERN = r"^[a-z]{2}_[A-Z]{2}$"
SINGLE_LETTER_WORDS = frozenset({"a", "i"})

_LEMMA = re.compile(LEMMA_PATTERN)


def is_valid_lemma(lemma: str) -> bool:
    return bool(_LEMMA.fullmatch(lemma)) and (len(lemma) > 1 or lemma in SINGLE_LETTER_WORDS)
