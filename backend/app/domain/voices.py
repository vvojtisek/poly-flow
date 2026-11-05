"""Speech voices a learner can choose, and the interest topics of a profile. Pure data.

A voice is a Piper voice installed by the `models` compose service. Only voices listed here can
be chosen; the first voice of each language is its default. Keep in sync with PIPER_VOICES in
docker/piper/Dockerfile and docker/models/models.spec.json (tests/test_tts.py checks both).
Adding a voice means: add it to the model spec, run `scripts/models.py lock`, add it to
PIPER_VOICES and to CATALOG below.
"""

from dataclasses import dataclass

from app.domain.enums import Language
from app.domain.language_packs import PACKS


@dataclass(frozen=True)
class Voice:
    id: str  # Piper model name
    language: Language
    name: str  # the speaker's name as the voice is published
    gender: str  # "female" | "male": what the learner hears, used only for the label


CATALOG: tuple[Voice, ...] = (
    Voice("de_DE-thorsten-medium", Language.DE, "Thorsten", "male"),
    Voice("fr_FR-siwis-medium", Language.FR, "Siwis", "female"),
    Voice("it_IT-paola-medium", Language.IT, "Paola", "female"),
    Voice("en_GB-jenny_dioco-medium", Language.EN, "Jenny", "female"),
)
BY_ID: dict[str, Voice] = {v.id: v for v in CATALOG}

DEFAULT_VOICES: dict[Language, str] = {}
for _v in CATALOG:
    DEFAULT_VOICES.setdefault(_v.language, _v.id)

# Spoken by the preview button; fixed text, so the sample endpoint is no general TTS proxy.
SAMPLES: dict[Language, str] = {lang: p.voice_sample for lang, p in PACKS.items()}


def voice_for(language: Language, chosen: str | None) -> str:
    """The chosen voice when it speaks `language`, else the language's default."""
    voice = BY_ID.get(chosen or "")
    return voice.id if voice and voice.language == language else DEFAULT_VOICES[language]


# Predefined interest topics (Czech labels live in the frontend localization table). A profile
# may add its own keywords next to these.
TOPICS: tuple[str, ...] = (
    "daily-life",
    "family",
    "food",
    "travel",
    "nature",
    "animals",
    "sports",
    "music",
    "culture",
    "science",
    "technology",
    "business",
)
MAX_INTERESTS = 20
MAX_KEYWORD_CHARS = 40
