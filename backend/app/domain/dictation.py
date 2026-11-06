"""Dictation (Diktát): compare a typed sentence with the spoken one. Pure functions; no I/O.

Practice only: the result is shown to the learner and never stored as knowledge evidence (only
Ověření is evidence). Each word gets a verdict the UI can colour: right, case only, accents only,
wrong, missing, extra.
"""

import difflib
import re
import unicodedata
from dataclasses import dataclass

_WORD = re.compile(r"[\w'\u2019-]+", re.UNICODE)


def tokens(text: str) -> list[str]:
    return _WORD.findall(unicodedata.normalize("NFC", text))


def _fold(w: str) -> str:
    d = unicodedata.normalize("NFD", w.lower().replace("ß", "ss").replace("\u2019", "'"))
    return "".join(c for c in d if unicodedata.category(c) != "Mn")


@dataclass(frozen=True, slots=True)
class Mark:
    expected: str | None  # None: an extra word the learner typed
    typed: str | None  # None: a word the learner left out
    verdict: str  # ok | case | accents | wrong | missing | extra


def compare(expected: str, typed: str) -> list[Mark]:
    exp, got = tokens(expected), tokens(typed)
    sm = difflib.SequenceMatcher(
        a=[_fold(w) for w in exp], b=[_fold(w) for w in got], autojunk=False
    )
    out: list[Mark] = []
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal":
            for e, g in zip(exp[i1:i2], got[j1:j2], strict=True):
                out.append(Mark(e, g, _verdict(e, g)))
        elif op == "replace":
            n = max(i2 - i1, j2 - j1)
            for k in range(n):
                e = exp[i1 + k] if i1 + k < i2 else None
                g = got[j1 + k] if j1 + k < j2 else None
                out.append(
                    Mark(e, g, "missing" if g is None else "extra" if e is None else "wrong")
                )
        elif op == "delete":
            out.extend(Mark(e, None, "missing") for e in exp[i1:i2])
        elif op == "insert":
            out.extend(Mark(None, g, "extra") for g in got[j1:j2])
    return out


def _verdict(e: str, g: str) -> str:
    if e == g:
        return "ok"
    if e.lower() == g.lower():
        return "case"
    return "accents"  # equal after folding: only accents/umlauts or ß differ


def score(marks: list[Mark]) -> float:
    """Share of the sentence's words written exactly (case and accents count)."""
    expected = [m for m in marks if m.expected is not None]
    if not expected:
        return 0.0
    extra = sum(1 for m in marks if m.verdict == "extra")
    ok = sum(1 for m in expected if m.verdict == "ok")
    return max(0.0, (ok - 0.5 * extra) / len(expected))
