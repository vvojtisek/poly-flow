"""Export a learner's own words: a spreadsheet CSV and an Anki-ready tab-separated file. Pure.

The spreadsheet file neutralises cells that a spreadsheet would run as a formula (=, +, -, @,
tab, carriage return at the start), the usual CSV-injection guard. The Anki file uses Anki's
file headers (separator, html off, tags column), so it imports without settings; tabs and line
breaks inside a field become spaces. The lexicon source travels with each word, so a drafted
(unreviewed) translation stays recognisable after export.
"""

import csv
import io
from dataclasses import dataclass
from typing import Literal

Format = Literal["csv", "anki"]

CSV_COLUMNS = (
    "lemma",
    "article",
    "translation_cs",
    "status",
    "part_of_speech",
    "frequency_rank",
    "example",
    "memory_hook",
    "next_review",
    "correct",
    "errors",
    "source",
)


@dataclass(frozen=True, slots=True)
class Row:
    lemma: str
    article: str | None  # der/die/das for German nouns, else None
    translation: str
    status: str
    pos: str
    rank: int
    example: str | None
    note: str | None
    next_review: str | None  # ISO date
    correct: int
    errors: int
    source: str | None  # lexicon provenance, e.g. polyflow-curated or claude-drafted


def _safe(value: object) -> str:
    text = "" if value is None else str(value)
    return "'" + text if text[:1] in ("=", "+", "-", "@", "\t", "\r") else text


def _flat(text: str | None) -> str:
    return " ".join((text or "").split())


def front(row: Row) -> str:
    return f"{row.article} {row.lemma}" if row.article else row.lemma


def to_csv(rows: list[Row]) -> str:
    out = io.StringIO()
    w = csv.writer(out, lineterminator="\r\n")
    w.writerow(CSV_COLUMNS)
    for r in rows:
        w.writerow(
            [
                _safe(v)
                for v in (
                    r.lemma,
                    r.article,
                    r.translation,
                    r.status,
                    r.pos,
                    r.rank,
                    r.example,
                    r.note,
                    r.next_review,
                    r.correct,
                    r.errors,
                    r.source,
                )
            ]
        )
    # A BOM so spreadsheet programs read the accents as UTF-8.
    return "﻿" + out.getvalue()


def to_anki(rows: list[Row], language: str) -> str:
    lines = ["#separator:tab", "#html:false", "#tags column:3"]
    for r in rows:
        back = _flat(r.translation)
        if r.note:
            back += f" ({_flat(r.note)})"
        tags = f"polyflow::{language} polyflow::{r.status}"
        if r.source:
            tags += f" polyflow::source::{'_'.join(r.source.split())}"
        lines.append("\t".join((_flat(front(r)), back, tags)))
    return "\n".join(lines) + "\n"
