"""Operational CLI.

python -m app.cli seed-lexicon data/lexicon/de.core100.csv [--dry-run]
python -m app.cli seed-blacklist data/blacklist/default.csv [--dry-run]
python -m app.cli seed-scenes data/scenes/de.core100.json [--dry-run]   (after seed-lexicon)
"""

import argparse
import asyncio
import csv
import json
import logging
import re
import sys
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Annotated, TypeVar

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    ValidationError,
    field_validator,
)
from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.session import dispose_engine, get_session
from app.domain.enums import (
    BlacklistCategory,
    BlacklistPatternType,
    CefrLevel,
    Language,
)
from app.domain.progression import frequency_band
from app.domain.scenes import SceneFile, lexicon_resolver, validate_scene_file
from app.models import ContentBlacklistEntry, LexiconItem, Scene, SceneWord

log = logging.getLogger("polyflow.cli")

NonEmpty = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
BATCH_SIZE = 500
T = TypeVar("T", bound=BaseModel)


def _blank_to_none(v: object) -> object:
    return None if isinstance(v, str) and not v.strip() else v


class LexiconRow(BaseModel):
    """One CSV row.

    Columns: language,rank,lemma,pos,translation_cs,ipa,cefr,gender,example
    and optionally source,license,revision (provenance).
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    language: Language
    rank: int = Field(ge=1)
    lemma: NonEmpty
    pos: str = ""
    translation_cs: NonEmpty
    ipa: str | None = None
    cefr: CefrLevel | None = None
    gender: str | None = None
    example: str | None = None
    source: str | None = None
    license: str | None = None
    revision: str | None = None

    _blanks = field_validator(
        "ipa", "cefr", "gender", "example", "source", "license", "revision", mode="before"
    )(_blank_to_none)

    @field_validator("pos")
    @classmethod
    def _upper_pos(cls, v: str) -> str:
        return v.upper()

    def to_db(self) -> dict:
        return {
            "language": self.language,
            "lemma": self.lemma,
            "pos": self.pos,
            "frequency_rank": self.rank,
            "frequency_band": frequency_band(self.rank),
            "translation_cs": self.translation_cs,
            "ipa": self.ipa,
            "cefr_level": self.cefr,
            "gender": self.gender,
            "example_sentence": self.example,
            "source": self.source,
            "license": self.license,
            "revision": self.revision,
        }


class BlacklistRow(BaseModel):
    """Columns: language (blank = all),pattern_type,pattern,category,note."""

    model_config = ConfigDict(str_strip_whitespace=True)

    language: Language | None = None
    pattern_type: BlacklistPatternType
    pattern: NonEmpty
    category: BlacklistCategory
    note: str | None = None

    _blanks = field_validator("language", "note", mode="before")(_blank_to_none)

    @field_validator("pattern")
    @classmethod
    def _compiles(cls, v: str, info) -> str:
        if info.data.get("pattern_type") == BlacklistPatternType.REGEX:
            try:
                re.compile(v)
            except re.error as exc:
                raise ValueError(f"invalid regex: {exc}") from exc
        return v

    def to_db(self) -> dict:
        return self.model_dump()


class RowError(Exception):
    pass


def read_rows(path: Path, model: type[T]) -> list[T]:
    rows: list[T] = []
    errors: list[str] = []
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(line for line in fh if not line.lstrip().startswith("#"))
        for row_no, raw in enumerate(reader, start=1):
            try:
                rows.append(model.model_validate(raw))
            except ValidationError as exc:
                msgs = "; ".join(
                    f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in exc.errors()
                )
                errors.append(f"{path} data row {row_no}: {msgs}")
    if errors:
        raise RowError("\n".join(errors))
    return rows


def check_lexicon_uniqueness(rows: Iterable[LexiconRow]) -> None:
    seen_rank: dict[tuple, int] = {}
    seen_key: set[tuple] = set()
    errors = []
    for r in rows:
        rk = (r.language, r.rank)
        key = (r.language, r.lemma, r.pos)
        if rk in seen_rank:
            errors.append(f"duplicate rank {r.rank} for {r.language.value}")
        if key in seen_key:
            errors.append(f"duplicate lemma {r.lemma!r}/{r.pos or '-'} for {r.language.value}")
        seen_rank[rk] = 1
        seen_key.add(key)
    if errors:
        raise RowError("\n".join(errors))


def _batches(items: Sequence[dict], size: int = BATCH_SIZE) -> Iterable[Sequence[dict]]:
    for i in range(0, len(items), size):
        yield items[i : i + size]


async def upsert_lexicon(rows: Sequence[LexiconRow]) -> int:
    table = LexiconItem.__table__
    updatable = [
        "frequency_rank",
        "frequency_band",
        "translation_cs",
        "ipa",
        "cefr_level",
        "gender",
        "example_sentence",
        "source",
        "license",
        "revision",
    ]
    async for session in get_session():
        async with session.begin():
            for batch in _batches([r.to_db() for r in rows]):
                stmt = insert(table).values(list(batch))
                stmt = stmt.on_conflict_do_update(
                    constraint="uq_lexicon_items_language_lemma_pos",
                    set_={c: stmt.excluded[c] for c in updatable} | {"updated_at": func.now()},
                )
                await session.execute(stmt)
    return len(rows)


async def upsert_blacklist(rows: Sequence[BlacklistRow]) -> int:
    table = ContentBlacklistEntry.__table__
    async for session in get_session():
        async with session.begin():
            for batch in _batches([r.to_db() for r in rows]):
                stmt = insert(table).values(list(batch))
                stmt = stmt.on_conflict_do_update(
                    constraint="uq_content_blacklist_pattern",
                    set_={
                        "category": stmt.excluded.category,
                        "note": stmt.excluded.note,
                        "is_active": True,
                        "updated_at": func.now(),
                    },
                )
                await session.execute(stmt)
    return len(rows)


def read_scene_file(path: Path) -> SceneFile:
    try:
        return SceneFile.model_validate(json.loads(path.read_text(encoding="utf-8")))
    except (ValueError, ValidationError) as exc:
        raise RowError(f"{path}: {exc}") from exc


async def upsert_scenes(f: SceneFile, *, dry_run: bool = False) -> int:
    """Validate against the lexicon in the database, then upsert by (language, slug).

    A scene's word list is replaced on every import. Scenes missing from the file are kept
    (finished lessons reference them).
    """
    async for session in get_session():
        async with session.begin():
            entries = (
                await session.execute(
                    select(LexiconItem.lemma, LexiconItem.pos, LexiconItem.id).where(
                        LexiconItem.language == f.language
                    )
                )
            ).all()
            resolve = lexicon_resolver(entries)
            if errors := validate_scene_file(f, resolve):
                raise RowError("\n".join(errors))
            if dry_run:
                return 0
            for position, s in enumerate(f.scenes, start=1):
                lines = [
                    {
                        "speaker": line.speaker,
                        "cs": line.cs,
                        "segments": [
                            {"t": seg.t, "item": str(resolve(seg.ref.lemma, seg.ref.pos))}
                            if seg.ref
                            else {"t": seg.t}
                            for seg in line.segments()
                        ],
                    }
                    for line in s.lines
                ]
                values = {
                    "language": f.language,
                    "slug": s.slug,
                    "position": position,
                    "title_cs": s.title_cs,
                    "lines": lines,
                    "source": f.source,
                    "revision": f.revision,
                }
                stmt = insert(Scene).values(values)
                stmt = stmt.on_conflict_do_update(
                    constraint="uq_scenes_language_slug",
                    set_={k: stmt.excluded[k] for k in ("position", "title_cs", "lines")}
                    | {"source": f.source, "revision": f.revision, "updated_at": func.now()},
                ).returning(Scene.id)
                scene_id = (await session.execute(stmt)).scalar_one()
                await session.execute(delete(SceneWord).where(SceneWord.scene_id == scene_id))
                # A word moved between scenes: the old scene must release it first.
                word_ids = [resolve(w.lemma, w.pos) for w in s.word_refs()]
                await session.execute(
                    delete(SceneWord).where(
                        SceneWord.lexicon_item_id.in_(word_ids),
                        SceneWord.scene_id.in_(
                            select(Scene.id).where(Scene.language == f.language)
                        ),
                    )
                )
                await session.execute(
                    insert(SceneWord).values(
                        [
                            {"scene_id": scene_id, "lexicon_item_id": wid, "position": n}
                            for n, wid in enumerate(word_ids)
                        ]
                    )
                )
    return len(f.scenes)


async def _seed_scenes(paths: list[Path], dry_run: bool) -> int:
    files = [read_scene_file(p) for p in paths]
    for f in files:
        n = await upsert_scenes(f, dry_run=dry_run)
        event = "scenes_validated" if dry_run else "scenes_seeded"
        log.info(event, extra={"language": f.language.value, "scenes": n or len(f.scenes)})
    return 0


async def _seed_lexicon(paths: list[Path], dry_run: bool) -> int:
    rows = [r for p in paths for r in read_rows(p, LexiconRow)]
    check_lexicon_uniqueness(rows)
    by_lang = {lang.value: sum(r.language == lang for r in rows) for lang in Language}
    if dry_run:
        log.info("lexicon_validated", extra={"rows": len(rows), "by_language": by_lang})
        return 0
    try:
        n = await upsert_lexicon(rows)
    except IntegrityError as exc:
        # Typically: an existing item (absent from this file) already holds an incoming rank.
        log.error("lexicon_seed_conflict", extra={"error": str(exc.orig)})
        return 1
    log.info("lexicon_seeded", extra={"rows": n, "by_language": by_lang})
    return 0


async def _seed_blacklist(paths: list[Path], dry_run: bool) -> int:
    rows = [r for p in paths for r in read_rows(p, BlacklistRow)]
    if dry_run:
        log.info("blacklist_validated", extra={"rows": len(rows)})
        return 0
    n = await upsert_blacklist(rows)
    log.info("blacklist_seeded", extra={"rows": n})
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="polyflow")
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name, help_ in (
        ("seed-lexicon", "Upsert lexicon items from CSV files"),
        ("seed-blacklist", "Upsert content blacklist entries from CSV files"),
        ("seed-scenes", "Upsert lesson scenes from JSON files (needs the lexicon)"),
    ):
        p = sub.add_parser(name, help=help_)
        p.add_argument("paths", nargs="+", type=Path)
        p.add_argument("--dry-run", action="store_true", help="Validate only; no DB writes")
    args = parser.parse_args(argv)

    configure_logging(get_settings().log_level)
    handler = {
        "seed-lexicon": _seed_lexicon,
        "seed-blacklist": _seed_blacklist,
        "seed-scenes": _seed_scenes,
    }[args.cmd]

    async def run() -> int:
        try:
            return await handler(args.paths, args.dry_run)
        finally:
            await dispose_engine()

    try:
        return asyncio.run(run())
    except RowError as exc:
        log.error("validation_failed", extra={"errors": str(exc).splitlines()})
        return 2


if __name__ == "__main__":
    sys.exit(main())
