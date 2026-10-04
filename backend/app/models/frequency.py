from sqlalchemy import CheckConstraint, Integer, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.domain.enums import ContentFlag
from app.domain.lemmas import LEMMA_PATTERN, LOCALE_PATTERN

_FLAG_VALUES = ", ".join(f"'{f.value}'" for f in ContentFlag)


class FrequencyLemma(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A corpus frequency rank for a lemma (data/frequency). Reference data, not curriculum.

    Rows have no Czech gloss, so lessons, checks, exams and the placement test never draw
    from this table; a lexicon item takes its rank from here once it has a reviewed gloss.
    """

    __tablename__ = "frequency_lemmas"
    __table_args__ = (
        # Also the lookup index: existence checks are an index scan on (locale, lemma).
        UniqueConstraint("locale", "lemma", name="uq_frequency_lemmas_locale_lemma"),
        # Deferred so a re-import that shifts ranks only needs consistency at commit.
        UniqueConstraint(
            "locale",
            "rank",
            name="uq_frequency_lemmas_locale_rank",
            deferrable=True,
            initially="DEFERRED",
        ),
        CheckConstraint("rank >= 1", name="rank_positive"),
        CheckConstraint(f"lemma ~ '{LEMMA_PATTERN}'", name="lemma_normalised"),
        CheckConstraint(f"locale ~ '{LOCALE_PATTERN}'", name="locale_format"),
        CheckConstraint(
            f"content_flags <@ ARRAY[{_FLAG_VALUES}]::varchar[]", name="content_flags_known"
        ),
    )

    locale: Mapped[str] = mapped_column(String(8), nullable=False)
    lemma: Mapped[str] = mapped_column(String(64), nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    # Milestone the rank falls in (app.domain.progression.frequency_band); set by the importer.
    frequency_band: Mapped[int] = mapped_column(Integer, nullable=False)
    # Universal POS tag of the lemma's most frequent use; heuristic, NULL when unknown.
    pos: Mapped[str | None] = mapped_column(String(16))
    # Same values and child-profile meaning as LexiconItem.content_flags.
    content_flags: Mapped[list[str]] = mapped_column(
        ARRAY(String(16)), default=list, server_default=text("'{}'::varchar[]"), nullable=False
    )
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    license: Mapped[str] = mapped_column(String(32), nullable=False)
    revision: Mapped[str] = mapped_column(String(32), nullable=False)
