"""Committed curated story files: schema, stretch-word rules and cross-language parity."""

import json
from pathlib import Path

import pytest

from app.domain.story_library import (
    StoryFile,
    validate_counts,
    validate_parity,
    validate_story_file,
)

DATA = Path(__file__).resolve().parents[1] / "data"
FILES = sorted((DATA / "stories").glob("*.stories.json"))


def _load(path: Path) -> StoryFile:
    return StoryFile.model_validate(json.loads(path.read_text(encoding="utf-8")))


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.name)
def test_story_file_is_valid(path: Path):
    f = _load(path)
    assert path.name == f"{f.language.value}.stories.json"
    assert validate_story_file(f) == []


def test_languages_have_the_same_plots():
    files = [_load(p) for p in FILES]
    assert {f.language.value for f in files} == {"de", "fr", "it", "en"}
    assert validate_parity(files) == []


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.name)
def test_expected_stories_per_level(path: Path):
    assert validate_counts(_load(path)) == []
