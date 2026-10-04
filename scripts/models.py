#!/usr/bin/env python3
"""Pinned, checksum-verified downloads of the TTS voices and STT models.

    python scripts/models.py lock                     # models.spec.json -> models.lock.json
    python scripts/models.py fetch --dest DIR [SEL]   # download missing/changed files, verify
    python scripts/models.py verify --dest DIR [SEL]  # re-hash every selected file

fetch makes no network call when every selected file is present and verified.
SEL selects models by name prefix, e.g. `piper/` or `whisper/small` (default: the whole lock).
Files land in DIR/<dir>/; <dir> comes from the lock (`piper`, or `whisper/<size>`).
Standard library only, so it runs in a bare python image and on the host.
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
SPEC = ROOT / "docker" / "models" / "models.spec.json"
LOCK = ROOT / "docker" / "models" / "models.lock.json"
HF = os.environ.get("HF_ENDPOINT", "https://huggingface.co")
MARKER = ".models-lock.json"  # per directory: {filename: sha256} of files already verified
CHUNK = 1 << 20


def _request(url: str) -> urllib.request.Request:
    req = urllib.request.Request(url, headers={"User-Agent": "polyflow-models/1"})
    if token := os.environ.get("HF_TOKEN"):
        req.add_header("Authorization", f"Bearer {token}")
    return req


def _get_json(url: str) -> Any:
    with urllib.request.urlopen(_request(url), timeout=60) as resp:
        return json.load(resp)


def _download(url: str, target: Path, expect_sha: str | None, expect_size: int | None) -> str:
    """Stream url into target atomically; return its sha256. Raises on any mismatch."""
    target.parent.mkdir(parents=True, exist_ok=True)
    last: Exception | None = None
    for attempt in range(4):
        if attempt:
            time.sleep(2**attempt)
        fd, tmp_name = tempfile.mkstemp(dir=target.parent, prefix=f".{target.name}.")
        tmp = Path(tmp_name)
        try:
            digest, size = hashlib.sha256(), 0
            with (
                os.fdopen(fd, "wb") as out,
                urllib.request.urlopen(_request(url), timeout=120) as resp,
            ):
                while chunk := resp.read(CHUNK):
                    digest.update(chunk)
                    out.write(chunk)
                    size += len(chunk)
            sha = digest.hexdigest()
            if expect_size is not None and size != expect_size:
                raise ValueError(f"{target.name}: size {size} != locked {expect_size}")
            if expect_sha is not None and sha != expect_sha:
                raise ValueError(f"{target.name}: sha256 {sha} != locked {expect_sha}")
            tmp.chmod(0o644)
            tmp.replace(target)
            return sha
        except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
            last = exc
            print(f"  retry {attempt + 1}: {exc}", file=sys.stderr)
        finally:
            tmp.unlink(missing_ok=True)
    raise RuntimeError(f"download failed: {url}: {last}")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


def _resolve_url(repo: str, revision: str, path: str) -> str:
    return f"{HF}/{repo}/resolve/{revision}/{path}"


# --- lock -------------------------------------------------------------------------------------


def lock(spec_path: Path, lock_path: Path) -> None:
    spec = json.loads(spec_path.read_text())
    out: list[dict[str, Any]] = []
    for model in spec["models"]:
        info = _get_json(f"{HF}/api/models/{model['repo']}/revision/{model['ref']}?blobs=true")
        revision = info["sha"]
        siblings = {s["rfilename"]: s for s in info.get("siblings", [])}
        if "files" in model:
            wanted = [(f["path"], f.get("as", Path(f["path"]).name)) for f in model["files"]]
            directory = model.get("dir", model["name"].split("/")[0])
        else:
            wanted = [
                (name, name)
                for name in sorted(siblings)
                if any(fnmatch.fnmatch(name, p) for p in model["patterns"])
            ]
            directory = model.get("dir", model["name"])
        if not wanted:
            raise SystemExit(f"{model['name']}: no files matched in {model['repo']}@{revision}")
        files = []
        for path, as_name in wanted:
            sib = siblings.get(path)
            if sib is None:
                raise SystemExit(f"{model['name']}: {path} not found in {model['repo']}@{revision}")
            lfs = sib.get("lfs") or {}
            sha, size = lfs.get("sha256"), lfs.get("size", sib.get("size"))
            if sha is None:  # small git (non-LFS) file: hash it ourselves
                with tempfile.TemporaryDirectory() as tmpdir:
                    tmp = Path(tmpdir) / "f"
                    sha = _download(_resolve_url(model["repo"], revision, path), tmp, None, None)
                    size = tmp.stat().st_size
            files.append({"path": path, "as": as_name, "size": size, "sha256": sha})
            print(f"  {model['name']}: {as_name} {size} {sha[:12]}")
        out.append(
            {
                "name": model["name"],
                "repo": model["repo"],
                "revision": revision,
                "dir": directory,
                "files": files,
            }
        )
        print(f"locked {model['name']} @ {revision}")
    lock_path.write_text(json.dumps({"version": 1, "models": out}, indent=2) + "\n")
    print(f"wrote {lock_path}")


# --- fetch / verify ---------------------------------------------------------------------------


def _selected(lock_data: dict[str, Any], selectors: list[str]) -> list[dict[str, Any]]:
    models = lock_data["models"]
    if not selectors:
        return models
    chosen = [m for m in models if any(m["name"].startswith(s) for s in selectors)]
    missing = [s for s in selectors if not any(m["name"].startswith(s) for m in models)]
    if missing:
        known = ", ".join(m["name"] for m in models)
        raise SystemExit(f"not in lock: {', '.join(missing)} (known: {known})")
    return chosen


def _read_marker(directory: Path) -> dict[str, dict[str, Any]]:
    try:
        return json.loads((directory / MARKER).read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _write_marker(directory: Path, marker: dict[str, dict[str, Any]]) -> None:
    tmp = directory / f"{MARKER}.tmp"
    tmp.write_text(json.dumps(marker, indent=2, sort_keys=True) + "\n")
    tmp.replace(directory / MARKER)


def _matches(target: Path, f: dict[str, Any], seen: dict[str, Any] | None, rehash: bool) -> bool:
    """A file verified earlier and untouched since (same size and mtime) is not re-hashed."""
    if not target.is_file():
        return False
    st = target.stat()
    if st.st_size != f["size"]:
        return False
    seen = seen or {}
    unchanged = seen.get("sha256") == f["sha256"] and seen.get("mtime_ns") == st.st_mtime_ns
    if unchanged and not rehash:
        return True
    return _sha256(target) == f["sha256"]


def fetch(lock_data: dict[str, Any], dest: Path, selectors: list[str], full_verify: bool) -> int:
    failures = 0
    for model in _selected(lock_data, selectors):
        directory = dest / model["dir"]
        directory.mkdir(parents=True, exist_ok=True)
        marker = _read_marker(directory)
        for f in model["files"]:
            target = directory / f["as"]
            if _matches(target, f, marker.get(f["as"]), rehash=full_verify):
                state = "ok"
            elif full_verify:
                state, failures = "MISMATCH", failures + 1
                marker.pop(f["as"], None)
            else:
                url = _resolve_url(model["repo"], model["revision"], f["path"])
                _download(url, target, f["sha256"], f["size"])
                state = "downloaded"
            if state != "MISMATCH":
                marker[f["as"]] = {"sha256": f["sha256"], "mtime_ns": target.stat().st_mtime_ns}
            print(f"{state:>10}  {model['name']}  {f['as']}")
        _write_marker(directory, marker)
    return failures


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_lock = sub.add_parser("lock")
    p_lock.add_argument("--spec", type=Path, default=SPEC)
    p_lock.add_argument("--lock", type=Path, default=LOCK)
    for name in ("fetch", "verify"):
        p = sub.add_parser(name)
        p.add_argument("--dest", type=Path, required=True)
        p.add_argument("--lock", type=Path, default=LOCK)
        p.add_argument("selectors", nargs="*")
    args = parser.parse_args()

    if args.cmd == "lock":
        lock(args.spec, args.lock)
        return
    if not args.lock.is_file():
        raise SystemExit(f"{args.lock} missing: run `scripts/models.py lock` with network access")
    lock_data = json.loads(args.lock.read_text())
    try:
        failures = fetch(lock_data, args.dest, args.selectors, full_verify=args.cmd == "verify")
    except (RuntimeError, ValueError) as exc:
        raise SystemExit(f"error: {exc}") from None
    if failures:
        raise SystemExit(f"{failures} file(s) do not match the lock")


if __name__ == "__main__":
    main()
