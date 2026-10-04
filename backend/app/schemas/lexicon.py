import uuid
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints

from app.domain.enums import CefrLevel, ContentFlag, Language

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]


class LexiconItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    language: Language
    lemma: str
    pos: str
    frequency_rank: int
    translation_cs: str
    ipa: str | None
    gender: str | None
    cefr_level: CefrLevel | None
    example_sentence: str | None
    content_flags: list[ContentFlag]


class LexiconItemUpdate(BaseModel):
    """Admin edits to shared content. Omitted fields stay; null clears an optional field.

    A later CSV re-import overwrites gloss/IPA/gender/example but only adds content flags.
    """

    model_config = ConfigDict(extra="forbid")

    translation_cs: Text | None = None
    ipa: Annotated[str, StringConstraints(strip_whitespace=True, max_length=128)] | None = None
    gender: Annotated[str, StringConstraints(strip_whitespace=True, max_length=8)] | None = None
    example_sentence: (
        Annotated[str, StringConstraints(strip_whitespace=True, max_length=512)] | None
    ) = None
    content_flags: list[ContentFlag] | None = None
