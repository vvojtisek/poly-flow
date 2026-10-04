"""Committed scene files must parse, resolve against the committed lexicon and cover it."""

import json
from pathlib import Path

import pytest

from app.cli import LexiconRow, read_rows
from app.domain.scenes import SceneFile, SceneLine, lexicon_resolver, validate_scene_file

DATA = Path(__file__).resolve().parents[1] / "data"
SCENE_FILES = sorted((DATA / "scenes").glob("*.json"))


def _lexicon(language: str) -> list[LexiconRow]:
    return [
        r
        for p in sorted((DATA / "lexicon").glob(f"{language}.*.csv"))
        for r in read_rows(p, LexiconRow)
    ]


def test_markup_segments():
    line = SceneLine(text="Hallo! [Ich] [bin|sein] [sie|sie/PRON].", cs="x")
    segs = line.segments()
    assert [s.t for s in segs] == ["Hallo! ", "Ich", " ", "bin", " ", "sie", "."]
    assert segs[3].ref.lemma == "sein" and segs[5].ref.pos == "PRON"
    assert line.plain() == "Hallo! Ich bin sie."
    with pytest.raises(ValueError):
        SceneLine(text="[kaputt", cs="x")


@pytest.mark.parametrize("path", SCENE_FILES, ids=lambda p: p.name)
def test_scene_file_is_valid_and_covers_core(path: Path):
    f = SceneFile.model_validate(json.loads(path.read_text(encoding="utf-8")))
    rows = _lexicon(f.language.value)
    resolve = lexicon_resolver((r.lemma, r.pos, (r.lemma, r.pos)) for r in rows)
    assert validate_scene_file(f, resolve) == []
    introduced = {resolve(w.lemma, w.pos) for s in f.scenes for w in s.word_refs()}
    missing = [
        f"{r.lemma}/{r.pos}" for r in rows if r.rank <= 100 and (r.lemma, r.pos) not in introduced
    ]
    assert missing == [], f"core-100 words without a scene: {missing}"
