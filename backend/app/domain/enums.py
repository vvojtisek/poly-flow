import enum


class Language(enum.StrEnum):
    DE = "de"
    FR = "fr"
    IT = "it"
    EN = "en"


class UserRole(enum.StrEnum):
    ADMIN = "admin"
    LEARNER = "learner"


class ContentFlag(enum.StrEnum):
    """Why a lexicon item is withheld from child profiles (age-appropriate filter)."""

    SEXUAL = "sexual"
    PROFANITY = "profanity"
    VIOLENCE = "violence"


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


GRAMMAR_GATE_WORDS = 1000
DECAY_AFTER_DAYS = 30
