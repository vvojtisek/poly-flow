import enum


class Language(enum.StrEnum):
    DE = "de"
    FR = "fr"
    IT = "it"


class UserRole(enum.StrEnum):
    ADMIN = "admin"
    LEARNER = "learner"


class CefrLevel(enum.StrEnum):
    A1 = "A1"
    A2 = "A2"
    B1 = "B1"
    B2 = "B2"
    C1 = "C1"
    C2 = "C2"


class ProgressState(enum.StrEnum):
    NEW = "NEW"
    LEARNING = "LEARNING"
    MASTERED = "MASTERED"


class BlacklistPatternType(enum.StrEnum):
    KEYWORD = "keyword"  # whole-word, case-insensitive
    REGEX = "regex"  # Python `re` syntax, compiled with re.IGNORECASE


class BlacklistCategory(enum.StrEnum):
    VIOLENCE = "violence"
    ADULT = "adult"
    POLITICS = "politics"
    OTHER = "other"


class StorySource(enum.StrEnum):
    RSS_NEWS = "rss_news"
    FAIRY_TALE = "fairy_tale"
    MYTH = "myth"


class StoryStatus(enum.StrEnum):
    PENDING = "pending"
    GENERATED = "generated"
    REJECTED = "rejected"  # failed the content blacklist
    FAILED = "failed"


MAX_FREQUENCY_RANK = 2500
# Fixed milestones; an item's band is the smallest bound >= its rank.
FREQUENCY_BANDS: tuple[int, ...] = (100, 500, 1000, 1500, 2000, 2500)
GRAMMAR_GATE_WORDS = 1000
DECAY_AFTER_DAYS = 30


def frequency_band(rank: int) -> int:
    if not 1 <= rank <= MAX_FREQUENCY_RANK:
        raise ValueError(f"rank {rank} outside 1..{MAX_FREQUENCY_RANK}")
    return next(b for b in FREQUENCY_BANDS if rank <= b)
