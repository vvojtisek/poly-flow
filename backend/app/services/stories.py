"""Generated stories and dialogues from the learner's own words (plan M6).

One reading text per profile, language and local day (`daily_stories`). It needs a configured
local model; child profiles get one only when `llm_for_children` is set, and then only after the
content checks. Reading and its questions are learning, not testing: answers are never evidence.
"""

import logging
import random
import uuid
from dataclasses import dataclass
from datetime import date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain import stories as dom
from app.domain.enums import Language, StorySource, StoryStatus
from app.models import (
    DailyStory,
    LexiconItem,
    User,
    UserWordProgress,
    WordCollection,
    WordCollectionItem,
)
from app.services.learning import LearningError, _suitable
from app.services.llm import Llm, LlmUnavailable
from app.services.safety import blacklist_hits
from app.services.tutor import LANGUAGE_CS, model_allowed

log = logging.getLogger("polyflow.stories")
KINDS = ("story", "dialogue")
CONTENT_POS = frozenset({"NOUN", "VERB", "ADJ", "ADV"})


@dataclass(slots=True)
class Words:
    known: list[str]
    targets: list[LexiconItem]


def local_day(user: User, now: datetime) -> date:
    return now.astimezone(ZoneInfo(user.timezone)).date()


def level_for(known_count: int) -> str:
    """Indicative level for the prompt only; vocabulary size alone is not a CEFR level."""
    if known_count < 500:
        return "A1"
    if known_count < 1000:
        return "A2"
    if known_count < 2500:
        return "B1"
    return "B2"


async def pick_words(db: AsyncSession, user: User, language: Language) -> Words:
    """Known = words the learner has met; targets = met but not yet known passively."""
    rows = (
        await db.execute(
            select(LexiconItem, UserWordProgress)
            .join(UserWordProgress, UserWordProgress.lexicon_item_id == LexiconItem.id)
            .where(
                UserWordProgress.user_id == user.id,
                LexiconItem.language == language,
                UserWordProgress.first_seen_at.is_not(None),
                _suitable(user, LexiconItem),
            )
            .order_by(LexiconItem.frequency_rank)
        )
    ).all()
    known = [item.lemma for item, p in rows if p.passive_known]
    learning = [(item, p) for item, p in rows if not p.passive_known]
    # Most error-prone first, then most recently seen; fill up from known words.
    # Content words make better targets than function words (a story "about" oder is odd).
    learning.sort(
        key=lambda r: (
            r[0].pos in CONTENT_POS,
            r[1].error_count,
            r[1].last_seen_at or r[1].first_seen_at,
        ),
        reverse=True,
    )
    targets = [item for item, _ in learning[: dom.STORY_POLICY.targets_max]]
    if len(targets) < dom.STORY_POLICY.targets_min:
        extra = [item for item, p in rows if p.passive_known and item not in targets]
        targets += extra[: dom.STORY_POLICY.targets_min - len(targets)]
    target_lemmas = {t.lemma for t in targets}
    known = [w for w in known if w not in target_lemmas][: dom.STORY_POLICY.known_words_max]
    return Words(known=known, targets=targets)


async def collection_targets(
    db: AsyncSession, user: User, language: Language, collection_id: uuid.UUID
) -> tuple[WordCollection, list[LexiconItem]]:
    collection = await db.scalar(
        select(WordCollection).where(
            WordCollection.id == collection_id,
            WordCollection.user_id == user.id,
            WordCollection.language == language,
        )
    )
    if collection is None:
        raise LearningError("collection_not_found", 404)
    items = (
        (
            await db.execute(
                select(LexiconItem)
                .join(WordCollectionItem, WordCollectionItem.lexicon_item_id == LexiconItem.id)
                .join(UserWordProgress, UserWordProgress.lexicon_item_id == LexiconItem.id)
                .where(
                    WordCollectionItem.collection_id == collection.id,
                    UserWordProgress.user_id == user.id,
                    UserWordProgress.first_seen_at.is_not(None),
                    LexiconItem.language == language,
                    _suitable(user),
                )
                .order_by(LexiconItem.frequency_rank, LexiconItem.id)
            )
        )
        .scalars()
        .all()
    )
    if len(items) < dom.STORY_POLICY.targets_min:
        raise LearningError("collection_too_small", 409)
    return collection, items[: dom.STORY_POLICY.targets_max]


async def today(
    db: AsyncSession, user: User, language: Language, now: datetime
) -> DailyStory | None:
    return (
        await db.execute(
            select(DailyStory).where(
                DailyStory.user_id == user.id,
                DailyStory.language == language,
                DailyStory.story_date == local_day(user, now),
            )
        )
    ).scalar_one_or_none()


async def archive(
    db: AsyncSession, user: User, language: Language, *, limit: int = 30
) -> list[DailyStory]:
    """Previously generated, safety-checked readings for this profile and language."""
    return list(
        (
            await db.scalars(
                select(DailyStory)
                .where(
                    DailyStory.user_id == user.id,
                    DailyStory.language == language,
                    DailyStory.status == StoryStatus.GENERATED,
                    DailyStory.source_type == StorySource.GENERATED,
                    DailyStory.safety_checked.is_(True),
                )
                .order_by(DailyStory.story_date.desc(), DailyStory.created_at.desc())
                .limit(limit)
            )
        ).all()
    )


async def get_story(
    db: AsyncSession, user: User, story_id: uuid.UUID, *, for_update: bool = False
) -> DailyStory:
    q = select(DailyStory).where(DailyStory.id == story_id, DailyStory.user_id == user.id)
    story = (await db.execute(q.with_for_update() if for_update else q)).scalar_one_or_none()
    if story is None or story.status != StoryStatus.GENERATED:
        raise LearningError("story_not_found", 404)
    return story


def _topic(user: User, day: date) -> str | None:
    interests = (user.settings or {}).get("interests") or []
    if not isinstance(interests, list) or not interests:
        return None
    return str(interests[day.toordinal() % len(interests)])


async def generate(
    db: AsyncSession,
    user: User,
    llm: Llm,
    language: Language,
    kind: str,
    now: datetime,
    collection_id: uuid.UUID | None = None,
) -> DailyStory:
    """Today's text: returned if it exists, otherwise written, validated and stored."""
    if kind not in KINDS:
        raise LearningError("kind_invalid", 422)
    selected_collection = None
    collection_words = None
    if collection_id is not None:
        selected_collection, collection_words = await collection_targets(
            db, user, language, collection_id
        )
    if not model_allowed(user, llm):
        raise LearningError("model_unavailable", 409)
    day = local_day(user, now)
    await db.execute(
        pg_insert(DailyStory)
        .values(
            id=uuid.uuid4(),
            user_id=user.id,
            language=language,
            story_date=day,
            status=StoryStatus.PENDING,
            source_type=StorySource.GENERATED,
        )
        .on_conflict_do_nothing(constraint="uq_daily_stories_user_lang_date")
    )
    try:
        story = (
            await db.execute(
                select(DailyStory)
                .where(
                    DailyStory.user_id == user.id,
                    DailyStory.language == language,
                    DailyStory.story_date == day,
                )
                .with_for_update(nowait=True)
            )
        ).scalar_one()
    except OperationalError as exc:  # another request is writing today's text right now
        raise LearningError("story_generating", 409) from exc
    if story.status == StoryStatus.GENERATED:
        return story

    words = await pick_words(db, user, language)
    collection_name = None
    topic = _topic(user, day)
    if selected_collection is not None and collection_words is not None:
        words.targets = collection_words
        words.known = [
            word for word in words.known if all(item.lemma != word for item in collection_words)
        ]
        collection_name = selected_collection.name
        topic = selected_collection.name
    if (
        len(words.targets) < dom.STORY_POLICY.targets_min
        or len(words.known) + len(words.targets) < dom.STORY_POLICY.known_words_min
    ):
        raise LearningError("not_enough_words", 409)
    targets = [t.lemma for t in words.targets]
    rng = random.Random(f"{user.id}:{day.isoformat()}")
    known = list(words.known)
    rng.shuffle(known)
    payload = dom.prompt_payload(
        LANGUAGE_CS[language],
        kind,
        level_for(len(words.known)),
        topic,
        known,
        targets,
    )
    failures: list[str] = []
    for _ in range(dom.STORY_POLICY.attempts):
        try:
            reply = await llm.chat(dom.SYSTEM_PROMPT, payload, max_tokens=1200, temperature=0.7)
        except LlmUnavailable as exc:
            failures.append(str(exc))
            break
        try:
            draft = dom.parse_draft(reply.text)
            cov = dom.check_draft(language, draft, known, targets)
        except dom.DraftInvalid as exc:
            failures.append(exc.code)
            continue
        everything = " ".join(
            [draft.title]
            + [f"{ln.speaker or ''} {ln.text} {ln.cs}" for ln in draft.lines]
            + [g.word + " " + g.cs for g in draft.glossary]
            + [q.question + " " + " ".join(q.options) for q in draft.questions]
        )
        if await blacklist_hits(db, everything, [language]):
            failures.append("blacklist")
            story.status = StoryStatus.REJECTED
            continue
        story.status = StoryStatus.GENERATED
        story.title = draft.title
        story.body = "\n".join(ln.text for ln in draft.lines)
        story.comprehension_questions = [q.model_dump() for q in draft.questions]
        story.new_item_ids = [t.id for t in words.targets]
        story.unknown_ratio = round(cov.unknown_ratio, 4)
        story.safety_checked = True
        story.llm_provider = reply.provider[:32]
        story.llm_model = reply.model[:64]
        story.generation_meta = {
            "kind": kind,
            "source_collection": collection_name,
            "prompt_version": dom.PROMPT_VERSION,
            "review_status": "unreviewed",
            "lines": [ln.model_dump() for ln in draft.lines],
            "glossary": [g.model_dump() for g in draft.glossary],
            "names": draft.names,
            "targets": targets,
            "unknown": cov.unknown[:20],
            "failures": failures,
            "answers": {},
        }
        log.info(
            "story_generated",
            extra={"language": language.value, "kind": kind, "attempts": len(failures) + 1},
        )
        return story
    if story.status != StoryStatus.REJECTED:
        story.status = StoryStatus.FAILED
    story.generation_meta = {
        "kind": kind,
        "source_collection": collection_name,
        "prompt_version": dom.PROMPT_VERSION,
        "failures": failures,
    }
    log.warning("story_failed", extra={"language": language.value, "failures": failures})
    raise LearningError("story_failed", 502)


def answer_question(story: DailyStory, index: int, choice: int) -> tuple[bool, int]:
    """Check a comprehension answer; the first answer per question is kept for the summary."""
    questions = story.comprehension_questions
    if not 0 <= index < len(questions):
        raise LearningError("question_not_found", 404)
    q = questions[index]
    if not 0 <= choice < len(q["options"]):
        raise LearningError("choice_invalid", 422)
    correct = choice == q["answer_index"]
    meta = dict(story.generation_meta)
    answers = dict(meta.get("answers") or {})
    answers.setdefault(str(index), correct)
    meta["answers"] = answers
    story.generation_meta = meta
    return correct, q["answer_index"]


def line_text(story: DailyStory, line: int) -> str:
    lines = story.generation_meta.get("lines") or []
    if not 0 <= line < len(lines):
        raise LearningError("audio_not_found", 404)
    return lines[line]["text"]
