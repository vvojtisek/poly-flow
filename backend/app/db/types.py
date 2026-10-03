"""Shared Postgres ENUM types. One instance per type so DDL is emitted exactly once."""

import enum

from sqlalchemy import Enum

from app.domain.enums import (
    BlacklistCategory,
    BlacklistPatternType,
    CefrLevel,
    Language,
    ProgressState,
    StorySource,
    StoryStatus,
    UserRole,
)


def _pg_enum(cls: type[enum.Enum], name: str) -> Enum:
    return Enum(cls, name=name, values_callable=lambda e: [m.value for m in e])


LanguageType = _pg_enum(Language, "language")
UserRoleType = _pg_enum(UserRole, "user_role")
CefrLevelType = _pg_enum(CefrLevel, "cefr_level")
ProgressStateType = _pg_enum(ProgressState, "progress_state")
BlacklistPatternTypeType = _pg_enum(BlacklistPatternType, "blacklist_pattern_type")
BlacklistCategoryType = _pg_enum(BlacklistCategory, "blacklist_category")
StorySourceType = _pg_enum(StorySource, "story_source")
StoryStatusType = _pg_enum(StoryStatus, "story_status")
