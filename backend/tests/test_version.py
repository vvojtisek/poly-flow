import json
import re
import tomllib
from pathlib import Path

import pytest

from app import __version__
from app.core.config import get_settings
from app.core.version import short_sha

REPO = Path(__file__).resolve().parents[2]


def _pep440(semver: str) -> str:
    """1.0.0-alpha.1 -> 1.0.0a1, -beta.N -> bN, -rc.N -> rcN (same mapping as set-version.sh)."""
    tags = {"alpha": "a", "beta": "b", "rc": "rc"}
    return re.sub(r"-(alpha|beta|rc)\.(\d+)$", lambda m: tags[m[1]] + m[2], semver)


async def test_version_endpoint(client, monkeypatch):
    monkeypatch.setenv("POLYFLOW_GIT_SHA", "0123456789abcdef")
    monkeypatch.setenv("POLYFLOW_GIT_BRANCH", "main")
    get_settings.cache_clear()
    try:
        r = await client.get("/version")
    finally:
        get_settings.cache_clear()
    assert r.status_code == 200
    body = r.json()
    assert body["version"] == __version__
    assert body["channel"] == ("pre-release" if "-" in __version__ else "release")
    assert body["commit"] == "0123456"
    assert body["branch"] == "main"


async def test_version_defaults_to_unknown(client, monkeypatch):
    monkeypatch.delenv("POLYFLOW_GIT_SHA", raising=False)
    monkeypatch.delenv("POLYFLOW_GIT_BRANCH", raising=False)
    get_settings.cache_clear()
    try:
        body = (await client.get("/version")).json()
    finally:
        get_settings.cache_clear()
    assert body["commit"] == "unknown"
    assert body["branch"] == "unknown"


@pytest.mark.skipif(not (REPO / "VERSION").exists(), reason="needs the full repository checkout")
def test_versions_in_sync():
    """/VERSION is canonical; scripts/set-version.sh writes every copy."""
    canonical = (REPO / "VERSION").read_text().strip()
    assert __version__ == canonical
    assert json.loads((REPO / "frontend/package.json").read_text())["version"] == canonical
    pyproject = tomllib.loads((REPO / "backend/pyproject.toml").read_text())
    assert pyproject["project"]["version"] == _pep440(canonical)


def test_short_sha():
    assert short_sha("0123456789abcdef") == "0123456"
    assert short_sha("0123456789abcdef-dirty") == "0123456-dirty"
    assert short_sha("unknown") == "unknown"
