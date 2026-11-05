"""Language packs: everything language-specific about a target language, in one place.

The source language is always Czech. Adding a target language means: a `Language` enum value
(and a migration adding it to the `language` type), a `LanguagePack` here, a Piper voice in
`app.domain.voices.CATALOG`, lexicon/scene/grammar data files, and the keyboard characters in
`frontend/lib/keyboard.ts` (kept equal to `special_chars`/`alt_chars` by
`tests/test_language_packs.py`). Grading, the tutor and generated stories read the pack; they
do not test for a particular language.
"""

from dataclasses import dataclass, field

from app.domain.enums import Language


@dataclass(frozen=True, slots=True)
class LanguagePack:
    language: Language
    name_cs: str  # "němčina": the language as Czech names it (prompts, explanations)
    # Words accepted before a lemma in a written answer ("der Hund" for "Hund").
    citation_articles: tuple[str, ...]
    # Articles and determiners whose swap is an article/case error in grammar exercises.
    determiners: frozenset[str]
    # Keyboard fallbacks accepted as correct spellings: (real, typed instead, note key).
    spelling_variants: tuple[tuple[str, str, str], ...] = ()
    # Nouns carry a learnt article (gender), shown with the noun and checked in answers.
    # The same fallbacks read back inside whole sentences (grammar answers), lower case only.
    sentence_fallbacks: tuple[tuple[str, str], ...] = ()
    noun_genders: dict[str, str] = field(default_factory=dict)  # article -> Czech description
    capitalises_nouns: bool = False  # a lower-case noun is a spelling mistake (German)
    # Characters a Czech keyboard lacks: the answer bar and Alt+letter (lower, upper).
    special_chars: tuple[str, ...] = ()
    alt_chars: dict[str, tuple[str, str]] = field(default_factory=dict)
    # Generated stories: forms a stem match cannot reach (lemma -> forms) and free words.
    irregular_forms: dict[str, tuple[str, ...]] = field(default_factory=dict)
    free_words: frozenset[str] = frozenset()
    voice_sample: str = ""  # spoken by the voice preview in the settings
    # Czech tutor hints per mistake kind (app.domain.grammar.ErrorTag value) for this language.
    tag_hints: dict[str, str] = field(default_factory=dict)

    @property
    def definite_articles(self) -> tuple[str, ...]:
        return tuple(self.noun_genders)

    def unfallback(self, text: str) -> str:
        """Learner sentence with keyboard fallbacks (ae, ss, ...) read as the real characters."""
        for real, typed in self.sentence_fallbacks:
            text = text.replace(typed, real).replace(typed.capitalize(), real.upper())
        return text


GERMAN = LanguagePack(
    language=Language.DE,
    name_cs="němčina",
    citation_articles=("der", "die", "das", "ein", "eine"),
    determiners=frozenset(
        "der die das den dem des ein eine einen einem einer eines "
        "kein keine keinen keinem keiner keines".split()
    ),
    spelling_variants=(
        ("ß", "ss", "eszett_as_ss"),
        ("ä", "ae", "umlaut_as_e"),
        ("ö", "oe", "umlaut_as_e"),
        ("ü", "ue", "umlaut_as_e"),
        ("Ä", "Ae", "umlaut_as_e"),
        ("Ö", "Oe", "umlaut_as_e"),
        ("Ü", "Ue", "umlaut_as_e"),
    ),
    sentence_fallbacks=(("ß", "ss"), ("ä", "ae"), ("ö", "oe"), ("ü", "ue")),
    noun_genders={"der": "mužského rodu", "die": "ženského rodu", "das": "středního rodu"},
    capitalises_nouns=True,
    special_chars=("ä", "ö", "ü", "ß", "Ä", "Ö", "Ü"),
    alt_chars={"KeyA": ("ä", "Ä"), "KeyO": ("ö", "Ö"), "KeyU": ("ü", "Ü"), "KeyS": ("ß", "ẞ")},
    irregular_forms={
        # the verb and the possessive sein
        "sein": (
            *("bin", "bist", "ist", "sind", "seid", "war", "warst", "waren", "wart", "gewesen"),
            *("seine", "seinen", "seinem", "seiner", "seines"),
        ),
        "haben": ("habe", "hast", "hat", "habt", "hatte", "hatten", "hattest", "gehabt"),
        "werden": ("werde", "wirst", "wird", "werdet", "wurde", "wurden", "geworden"),
        "der": ("die", "das", "den", "dem", "des"),
        "ein": ("eine", "einen", "einem", "einer", "eines"),
        "kein": ("keine", "keinen", "keinem", "keiner", "keines"),
        "ich": ("mich", "mir"),
        "du": ("dich", "dir"),
        "er": ("ihn", "ihm"),
        "sie": ("ihr", "ihnen"),
        "wir": ("uns",),
        "mein": ("meine", "meinen", "meinem", "meiner", "meines"),
        "dein": ("deine", "deinen", "deinem", "deiner", "deines"),
        "können": ("kann", "kannst", "könnt", "konnte", "konnten"),
        "müssen": ("muss", "musst", "müsst", "musste", "mussten"),
        "wollen": ("will", "willst", "wollt", "wollte", "wollten"),
        "gehen": ("geht", "ging", "gingen", "gegangen"),
        "geben": ("gibt", "gibst", "gab", "gegeben"),
        "sehen": ("sieht", "siehst", "sah", "gesehen"),
        "essen": ("isst", "aß", "gegessen"),
        "fahren": ("fährt", "fährst", "fuhr", "gefahren"),
        "kommen": ("kam", "kamen", "gekommen"),
        "nehmen": ("nimmt", "nimmst", "nahm", "genommen"),
        "sprechen": ("spricht", "sprichst", "sprach", "gesprochen"),
        "lesen": ("liest", "las", "gelesen"),
        "wissen": ("weiß", "weißt", "wusste", "gewusst"),
        "mögen": ("mag", "magst", "mochte", "möchte", "möchtest", "möchten"),
    },
    free_words=frozenset({"ja", "nein", "oh", "hallo", "tschüss", "danke", "bitte", "ok"}),
    voice_sample="Hallo! So klingt meine Stimme. Wollen wir zusammen üben?",
    tag_hints={
        "article": "Chyba je ve členu: zkontroluj rod podstatného jména a pád, který věta "
        "vyžaduje (např. 4. pád po haben, sehen; 3. pád po mit, bei).",
        "word_order": "Slova máš správně, jen jejich pořadí ne. V německé oznamovací větě "
        "stojí časované sloveso na druhém místě, ve vedlejší větě na konci.",
        "capitalisation": "Podstatná jména se v němčině píšou vždy s velkým písmenem.",
        "diacritics": "Pozor na přehlásky a diakritiku: ä, ö, ü mění význam i výslovnost "
        "(schon = už, schön = hezký).",
    },
)

FRENCH = LanguagePack(
    language=Language.FR,
    name_cs="francouzština",
    citation_articles=("le", "la", "les", "l'", "un", "une"),
    determiners=frozenset("le la les l' un une des du de au aux".split()),
    spelling_variants=(("œ", "oe", "ligature_split"), ("æ", "ae", "ligature_split")),
    special_chars=("é", "è", "ê", "à", "â", "ç", "ô", "î", "û", "ù", "ë", "œ"),
    alt_chars={"KeyE": ("é", "É"), "KeyC": ("ç", "Ç"), "KeyA": ("à", "À"), "KeyO": ("œ", "Œ")},
    free_words=frozenset({"oui", "non", "oh", "bonjour", "salut", "merci"}),
    voice_sample="Bonjour ! Voici ma voix. On s'entraîne ensemble ?",
)

ITALIAN = LanguagePack(
    language=Language.IT,
    name_cs="italština",
    citation_articles=("il", "lo", "la", "i", "gli", "le", "l'", "un", "uno", "una", "un'"),
    determiners=frozenset("il lo la i gli le l' un uno una un' del della dei degli".split()),
    special_chars=("à", "è", "é", "ì", "ò", "ù"),
    alt_chars={
        "KeyE": ("è", "È"),
        "KeyA": ("à", "À"),
        "KeyO": ("ò", "Ò"),
        "KeyU": ("ù", "Ù"),
        "KeyI": ("ì", "Ì"),
    },
    free_words=frozenset({"sì", "no", "oh", "ciao", "grazie"}),
    voice_sample="Ciao! Questa è la mia voce. Ci esercitiamo insieme?",
)

ENGLISH = LanguagePack(
    language=Language.EN,
    name_cs="angličtina",
    # "to" is the infinitive marker, accepted before a bare verb ("to go" for "go")
    citation_articles=("the", "a", "an", "to"),
    determiners=frozenset("the a an".split()),
    free_words=frozenset({"yes", "no", "oh", "hello", "hi", "thanks", "ok"}),
    voice_sample="Hello! This is my voice. Shall we practise together?",
)

PACKS: dict[Language, LanguagePack] = {p.language: p for p in (GERMAN, FRENCH, ITALIAN, ENGLISH)}


def pack(language: Language) -> LanguagePack:
    return PACKS[language]
