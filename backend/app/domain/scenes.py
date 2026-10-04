"""Scene files (plan: learning before testing). Pure parsing and validation; no I/O.

A scene file holds the short dialogues that introduce words in context. Each line marks the
lexicon words it contains:

    [Hund]            surface form == lemma
    [bin|sein]        surface form, then the lemma
    [sie|sie/PRON]    lemma/UPOS when the lemma alone is ambiguous

`words` lists the lemmas a scene *introduces* (taught in its lessons). Every word is introduced
by at most one scene per language and must be marked at least once in that scene's lines.
"""

import re
from collections.abc import Callable, Iterable
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from app.domain.enums import Language

NonEmpty = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
MARK = re.compile(r"\[([^\[\]|]+)(?:\|([^\[\]/|]+)(?:/([A-Z]+))?)?\]")
SLUG = r"^[a-z0-9][a-z0-9-]{0,63}$"

# (lemma, pos) -> resolves to an id; returns None when missing, raises on ambiguity.
Resolver = Callable[[str, str | None], object | None]


class WordRef(BaseModel):
    lemma: str
    pos: str | None = None

    @classmethod
    def parse(cls, raw: str) -> "WordRef":
        lemma, _, pos = raw.strip().partition("/")
        return cls(lemma=lemma.strip(), pos=pos.strip().upper() or None)

    def __str__(self) -> str:
        return f"{self.lemma}/{self.pos}" if self.pos else self.lemma


class Segment(BaseModel):
    t: str
    ref: WordRef | None = None


class SceneLine(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    speaker: str | None = None
    text: NonEmpty  # target language, with [marks]
    cs: NonEmpty  # natural Czech translation

    @field_validator("text")
    @classmethod
    def _balanced(cls, v: str) -> str:
        stripped = MARK.sub("", v)
        if "[" in stripped or "]" in stripped:
            raise ValueError(f"malformed [mark] in {v!r}")
        return v

    def segments(self) -> list[Segment]:
        out: list[Segment] = []
        pos = 0
        for m in MARK.finditer(self.text):
            if m.start() > pos:
                out.append(Segment(t=self.text[pos : m.start()]))
            surface, lemma, upos = m.group(1), m.group(2), m.group(3)
            out.append(Segment(t=surface, ref=WordRef(lemma=(lemma or surface).strip(), pos=upos)))
            pos = m.end()
        if pos < len(self.text):
            out.append(Segment(t=self.text[pos:]))
        return out

    def plain(self) -> str:
        return "".join(s.t for s in self.segments())


class SceneIn(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    slug: Annotated[str, StringConstraints(pattern=SLUG)]
    title_cs: NonEmpty
    words: list[str] = Field(min_length=1)
    lines: list[SceneLine] = Field(min_length=2)

    def word_refs(self) -> list[WordRef]:
        return [WordRef.parse(w) for w in self.words]


class SceneFile(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    language: Language
    source: str | None = None
    revision: str | None = None
    scenes: list[SceneIn] = Field(min_length=1)


def _key(ref: WordRef, resolve: Resolver) -> object:
    return resolve(ref.lemma, ref.pos)


def validate_scene_file(f: SceneFile, resolve: Resolver) -> list[str]:
    """Errors (empty = valid). `resolve` maps a word reference to a lexicon key."""
    errors: list[str] = []
    slugs: set[str] = set()
    introduced: dict[object, str] = {}
    for s in f.scenes:
        where = f"{f.language.value}/{s.slug}"
        if s.slug in slugs:
            errors.append(f"{where}: duplicate slug")
        slugs.add(s.slug)

        marked: set[object] = set()
        for n, line in enumerate(s.lines, start=1):
            for seg in line.segments():
                if seg.ref is None:
                    continue
                try:
                    key = _key(seg.ref, resolve)
                except LookupError as exc:
                    errors.append(f"{where} line {n}: {exc}")
                    continue
                if key is None:
                    errors.append(f"{where} line {n}: [{seg.t}] -> {seg.ref} not in lexicon")
                else:
                    marked.add(key)

        for ref in s.word_refs():
            try:
                key = _key(ref, resolve)
            except LookupError as exc:
                errors.append(f"{where}: {exc}")
                continue
            if key is None:
                errors.append(f"{where}: word {ref} not in lexicon")
                continue
            if key in introduced:
                errors.append(f"{where}: word {ref} already introduced by {introduced[key]}")
            introduced[key] = s.slug
            if key not in marked:
                errors.append(f"{where}: word {ref} is never [marked] in the lines")
    return errors


def lexicon_resolver(entries: Iterable[tuple[str, str, object]]) -> Resolver:
    """Resolver over (lemma, pos, key) triples. A bare lemma must be unambiguous."""
    by_pair: dict[tuple[str, str], object] = {}
    by_lemma: dict[str, list[tuple[str, object]]] = {}
    for lemma, pos, key in entries:
        by_pair[(lemma, pos)] = key
        by_lemma.setdefault(lemma, []).append((pos, key))

    def resolve(lemma: str, pos: str | None) -> object | None:
        if pos is not None:
            return by_pair.get((lemma, pos))
        hits = by_lemma.get(lemma, [])
        if len(hits) > 1:
            options = ", ".join(f"{lemma}/{p}" for p, _ in hits)
            raise LookupError(f"{lemma!r} is ambiguous; write one of {options}")
        return hits[0][1] if hits else None

    return resolve
