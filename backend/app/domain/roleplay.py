"""Role-play over a lesson scene: the learner takes one speaker's part. Pure rules; no I/O.

The scene text is reviewed curriculum content; nothing here generates language. On the
learner's turn they see what they want to say (the Czech line) and pick the matching sentence
from three: the right one, a line from the same scene that does not fit this moment, and a line
of similar length from another scene. Choices are deterministic per scene, role and line, so a
reload shows the same options.
"""

import random
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Line:
    speaker: str | None
    text: str
    cs: str


def plain(line: dict) -> Line:
    """A stored scene line (segments) as plain text."""
    text = "".join(seg["t"] for seg in line.get("segments", ())) or line.get("text", "")
    return Line(line.get("speaker"), text.strip(), line.get("cs", ""))


def speakers(lines: list[Line]) -> list[str]:
    """Speakers in order of first appearance; a scene needs two to be played."""
    out: list[str] = []
    for ln in lines:
        if ln.speaker and ln.speaker not in out:
            out.append(ln.speaker)
    return out


def playable(lines: list[Line]) -> bool:
    return len(speakers(lines)) >= 2 and all(ln.speaker for ln in lines)


def _norm(s: str) -> str:
    return " ".join(s.lower().split())


def options(
    lines: list[Line], index: int, other_scenes: list[str], seed: str, k: int = 3
) -> tuple[list[str], int]:
    """Choices for the line at `index` and the position of the right one."""
    target = lines[index].text
    rng = random.Random(f"{seed}:{index}")
    seen = {_norm(target)}
    picks: list[str] = []

    def take(pool: list[str]) -> None:
        pool = [p for p in pool if _norm(p) not in seen]
        if not pool:
            return
        # Similar length reads as a real alternative, not an obvious odd one out.
        pool.sort(key=lambda p: (abs(len(p) - len(target)), p))
        choice = rng.choice(pool[: max(3, len(pool) // 3)])
        seen.add(_norm(choice))
        picks.append(choice)

    take([ln.text for i, ln in enumerate(lines) if i != index])
    while len(picks) < k - 1:
        before = len(picks)
        take(other_scenes)
        if len(picks) == before:
            break
    choices = [target, *picks]
    rng.shuffle(choices)
    return choices, choices.index(target)
