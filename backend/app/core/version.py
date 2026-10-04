from typing import Literal

from pydantic import BaseModel

from app import __version__
from app.core.config import get_settings


class BuildInfo(BaseModel):
    version: str
    channel: Literal["release", "pre-release"]
    commit: str
    branch: str
    built_at: str | None
    env: str


def short_sha(sha: str) -> str:
    """abc1234…[-dirty] -> abc1234[-dirty]; anything that is not a hex SHA passes through."""
    head, dirty, _ = sha.partition("-dirty")
    if len(head) < 7 or any(c not in "0123456789abcdef" for c in head.lower()):
        return sha
    return head[:7] + dirty


def get_build_info() -> BuildInfo:
    s = get_settings()
    return BuildInfo(
        version=__version__,
        # SemVer: a hyphenated suffix (1.0.0-alpha.1) marks a pre-release.
        channel="pre-release" if "-" in __version__ else "release",
        commit=short_sha(s.git_sha),
        branch=s.git_branch,
        built_at=s.build_time or None,
        env=s.env,
    )
