"""Personal mastery ranks and achievements (single player). Pure rules; no I/O.

Vlad, 2026-11-06: a personal rank path from beginner to master, tied to concrete learning
achievements. This reverses the earlier drop of gamification (plan P6) only for this: there is no
currency, no leaderboard, no comparison with other profiles, no daily streak, no lives, and nothing
is lost for a day off.

- Every requirement is measured evidence: words verified in Ověření (passive and active), grammar
  units applied correctly in grammar checks, vocabulary level exams passed, and mistakes recovered
  (a word or grammar exercise missed in a check and later answered right in a check).
- A rank, once reached, is kept: decay schedules reviews but never demotes (like level badges).
- Grammar requirements apply only as far as the language has grammar units; a language without a
  grammar pack is not held back by it.
- Ranks are per language, like all progress. Names and the two themes (hockey, royal) are UI copy
  in the Czech localisation table; the server only knows rank numbers and requirement keys.
"""

from dataclasses import dataclass, field

from app.domain.enums import CefrLevel

PATHS = ("hockey", "royal")
DEFAULT_PATH = "hockey"


@dataclass(frozen=True, slots=True)
class Stats:
    known_words: int = 0  # passive and active both verified
    passive_words: int = 0  # recognised in checks on several days
    grammar_known: int = 0  # units applied correctly in checks often enough
    grammar_total: int = 0  # active units in the language (0 = no grammar pack)
    badges: frozenset[CefrLevel] = field(default_factory=frozenset)  # level exams passed
    recoveries: int = 0  # mistakes later answered right in a check
    checks_answered: int = 0  # graded first attempts (words and grammar)
    listening_right: int = 0  # spoken answers recognised as right


@dataclass(frozen=True, slots=True)
class Requirement:
    key: str  # "known_words" | "grammar_known" | "badge" | "recoveries"
    target: int  # for "badge": index of the CEFR level (A1=1 .. B2=4)

    def current(self, s: Stats) -> int:
        if self.key == "known_words":
            return s.known_words
        if self.key == "grammar_known":
            return s.grammar_known
        if self.key == "recoveries":
            return s.recoveries
        if self.key == "badge":
            return 1 if _BADGE_LEVEL[self.target] in s.badges else 0
        raise ValueError(self.key)

    def needed(self, s: Stats) -> int:
        """Target after capping grammar at what the language offers."""
        if self.key == "grammar_known":
            return min(self.target, s.grammar_total)
        if self.key == "badge":
            return 1
        return self.target

    def met(self, s: Stats) -> bool:
        return self.current(s) >= self.needed(s)

    def applies(self, s: Stats) -> bool:
        return not (self.key == "grammar_known" and s.grammar_total == 0)


_BADGE_LEVEL = {1: CefrLevel.A1, 2: CefrLevel.A2, 3: CefrLevel.B1, 4: CefrLevel.B2}


def _r(key: str, target: int) -> Requirement:
    return Requirement(key, target)


@dataclass(frozen=True, slots=True)
class Rank:
    number: int  # 1 = start
    tier: str  # emblem frame: bronze, silver, gold, platinum, diamond
    requirements: tuple[Requirement, ...]


# Thresholds follow the curriculum ladder: core 100, A1 (500, badge), A2 (1000, badge),
# B1 (2500, badge), B2 (5000, badge). Grammar targets follow the German skill tree (A1 12 units,
# A2 19 cumulative, B1 25, B2 30); other languages cap them at their own unit count.
RANKS: tuple[Rank, ...] = (
    Rank(1, "bronze", ()),
    Rank(2, "bronze", (_r("known_words", 25),)),
    Rank(3, "bronze", (_r("known_words", 100), _r("grammar_known", 2))),
    Rank(4, "silver", (_r("known_words", 250), _r("grammar_known", 5), _r("recoveries", 10))),
    Rank(5, "silver", (_r("known_words", 500), _r("badge", 1), _r("grammar_known", 12))),
    Rank(6, "gold", (_r("known_words", 750), _r("grammar_known", 15), _r("recoveries", 40))),
    Rank(7, "gold", (_r("known_words", 1000), _r("badge", 2), _r("grammar_known", 19))),
    Rank(8, "platinum", (_r("known_words", 2500), _r("badge", 3), _r("grammar_known", 25))),
    Rank(9, "platinum", (_r("known_words", 4000), _r("grammar_known", 28), _r("recoveries", 150))),
    Rank(10, "diamond", (_r("known_words", 5000), _r("badge", 4), _r("grammar_known", 30))),
)
MAX_RANK = RANKS[-1].number


def rank_for(s: Stats) -> int:
    """Highest rank whose requirements (and all lower ranks' requirements) hold now."""
    reached = 1
    for rank in RANKS[1:]:
        if all(req.met(s) for req in rank.requirements if req.applies(s)):
            reached = rank.number
        else:
            break
    return reached


def held_rank(s: Stats, recorded: int) -> int:
    """A rank once reached is kept: decay never demotes."""
    return max(rank_for(s), recorded, 1)


def progress_to(rank: Rank, s: Stats) -> list[dict]:
    """Each applicable requirement of `rank` with current value and target."""
    out = []
    for req in rank.requirements:
        if not req.applies(s):
            continue
        out.append(
            {
                "key": req.key,
                "target": req.needed(s),
                "current": min(req.current(s), req.needed(s)),
                "level": _BADGE_LEVEL[req.target].value if req.key == "badge" else None,
                "met": req.met(s),
            }
        )
    return out


# ---------------------------------------------------------------- achievements


@dataclass(frozen=True, slots=True)
class Achievement:
    key: str  # UI copy lives in the frontend
    group: str  # words, grammar, recovery, exams, practice

    def earned(self, s: Stats) -> bool:
        return _ACHIEVED[self.key](s)


_ACHIEVED = {
    "first_word": lambda s: s.known_words >= 1,
    "words_100": lambda s: s.known_words >= 100,
    "words_500": lambda s: s.known_words >= 500,
    "words_1000": lambda s: s.known_words >= 1000,
    "passive_250": lambda s: s.passive_words >= 250,
    "first_rule": lambda s: s.grammar_known >= 1,
    "rules_10": lambda s: s.grammar_known >= 10,
    "all_rules": lambda s: s.grammar_total > 0 and s.grammar_known >= s.grammar_total,
    "recover_1": lambda s: s.recoveries >= 1,
    "recover_25": lambda s: s.recoveries >= 25,
    "recover_100": lambda s: s.recoveries >= 100,
    "badge_a1": lambda s: CefrLevel.A1 in s.badges,
    "badge_a2": lambda s: CefrLevel.A2 in s.badges,
    "badge_b1": lambda s: CefrLevel.B1 in s.badges,
    "badge_b2": lambda s: CefrLevel.B2 in s.badges,
    "checks_500": lambda s: s.checks_answered >= 500,
    "voice_25": lambda s: s.listening_right >= 25,
}

_GROUPS = {
    "first_word": "words",
    "words_100": "words",
    "words_500": "words",
    "words_1000": "words",
    "passive_250": "words",
    "first_rule": "grammar",
    "rules_10": "grammar",
    "all_rules": "grammar",
    "recover_1": "recovery",
    "recover_25": "recovery",
    "recover_100": "recovery",
    "badge_a1": "exams",
    "badge_a2": "exams",
    "badge_b1": "exams",
    "badge_b2": "exams",
    "checks_500": "practice",
    "voice_25": "practice",
}

ACHIEVEMENTS: tuple[Achievement, ...] = tuple(Achievement(k, _GROUPS[k]) for k in _ACHIEVED)
