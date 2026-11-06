"""Minimal pairs: two words that differ in one sound a Czech ear tends to merge. Pure data.

Each set targets one contrast that Czech does not have or does not use the same way: German
ü/i, ö/e and vowel length; French u/ou and the nasal vowels; Italian single and double
consonants; English ship/sheep, th, w/v and final voiced consonants (Czech devoices them).

The learner hears one word of a pair (local speech synthesis) and picks which one it was.
Glosses are short Czech meanings so the learner knows both words are real; the set is drafted,
not yet reviewed by a native speaker. Practice only.
"""

from dataclasses import dataclass

from app.domain.enums import Language


@dataclass(frozen=True, slots=True)
class Word:
    text: str
    cs: str


@dataclass(frozen=True, slots=True)
class PairSet:
    id: str
    title: str  # Czech, shown on the set's button
    hint: str  # Czech: how to hear or make the difference
    pairs: tuple[tuple[Word, Word], ...]


def _p(a: str, a_cs: str, b: str, b_cs: str) -> tuple[Word, Word]:
    return (Word(a, a_cs), Word(b, b_cs))


SETS: dict[Language, tuple[PairSet, ...]] = {
    "de": (
        PairSet(
            "ue_i",
            "ü nebo i",
            "Při ü jsou rty zaokrouhlené jako na u, jazyk je jako na i.",
            (
                _p("Tür", "dveře", "Tier", "zvíře"),
                _p("küssen", "líbat", "Kissen", "polštář"),
                _p("fühlen", "cítit", "fielen", "padali"),
                _p("Bühne", "jeviště", "Biene", "včela"),
            ),
        ),
        PairSet(
            "ue_u",
            "ü nebo u",
            "u je vzadu jako české u; ü je vpředu jako i, jen se zaokrouhlenými rty.",
            (
                _p("Mütter", "matky", "Mutter", "matka"),
                _p("für", "pro", "fuhr", "jel"),
                _p("drücken", "tlačit", "drucken", "tisknout"),
            ),
        ),
        PairSet(
            "oe_e",
            "ö nebo e",
            "ö je e se zaokrouhlenými rty.",
            (
                _p("können", "moci", "kennen", "znát"),
                _p("lösen", "řešit", "lesen", "číst"),
                _p("Söhne", "synové", "Sehne", "šlacha"),
            ),
        ),
        PairSet(
            "length",
            "dlouhá nebo krátká",
            "Dlouhá samohláska je delší a zavřenější; po krátké často následuje"
            " zdvojená souhláska.",
            (
                _p("Staat", "stát", "Stadt", "město"),
                _p("Miete", "nájem", "Mitte", "střed"),
                _p("Ofen", "kamna", "offen", "otevřený"),
                _p("bieten", "nabízet", "bitten", "prosit"),
                _p("Hüte", "klobouky", "Hütte", "chata"),
            ),
        ),
        PairSet(
            "ie_ei",
            "ie nebo ei",
            "ie je dlouhé í, ei je aj.",
            (
                _p("Lied", "píseň", "Leid", "utrpení"),
                _p("fielen", "padali", "feilen", "pilovat"),
                _p("Miene", "výraz tváře", "meine", "moje"),
            ),
        ),
        PairSet(
            "ch_sch",
            "ch nebo sch",
            "Měkké ch je jen vydechnutí u horních zubů; sch je české š se zaokrouhlenými rty.",
            (
                _p("Kirche", "kostel", "Kirsche", "třešeň"),
                _p("mich", "mě", "misch", "míchej"),
            ),
        ),
    ),
    "fr": (
        PairSet(
            "u_ou",
            "u nebo ou",
            "ou je české u; u je i se zaokrouhlenými rty.",
            (
                _p("dessus", "nahoře", "dessous", "dole"),
                _p("tu", "ty", "tout", "všechno"),
                _p("rue", "ulice", "roue", "kolo"),
                _p("vu", "viděný", "vous", "vy"),
                _p("pur", "čistý", "pour", "pro"),
            ),
        ),
        PairSet(
            "nasal",
            "nosovky",
            "Tři nosové samohlásky: an/en (otevřené, vzadu), on (zaokrouhlené), in (jako e nosem).",
            (
                _p("vent", "vítr", "vont", "jdou"),
                _p("lent", "pomalý", "long", "dlouhý"),
                _p("bain", "koupel", "banc", "lavička"),
                _p("vin", "víno", "vent", "vítr"),
            ),
        ),
        PairSet(
            "oral_nasal",
            "nosovka nebo ne",
            "U nosovky jde vzduch i nosem a n se nevysloví.",
            (
                _p("bon", "dobrý", "beau", "krásný"),
                _p("vin", "víno", "vais", "jdu"),
            ),
        ),
        PairSet(
            "e_es",
            "le nebo les",
            "le, de, ce mají slabé e; les, des, ces mají zavřené é."
            " Rozlišuje jednotné a množné číslo.",
            (
                _p("le", "ten (člen)", "les", "ti (člen, množné)"),
                _p("de", "z, od", "des", "nějací (člen, množné)"),
                _p("ce", "tento", "ces", "tito"),
            ),
        ),
        PairSet(
            "eu_ou",
            "eu nebo ou",
            "eu je e se zaokrouhlenými rty; ou je české u.",
            (
                _p("deux", "dva", "doux", "jemný"),
                _p("peu", "málo", "pou", "veš"),
            ),
        ),
    ),
    "it": (
        PairSet(
            "double",
            "jedna nebo dvě souhlásky",
            "Zdvojená souhláska se drží déle (u p, t, k krátká pauza před ní). Mění význam.",
            (
                _p("pala", "lopata", "palla", "míč"),
                _p("caro", "drahý", "carro", "vůz"),
                _p("nono", "devátý", "nonno", "dědeček"),
                _p("sete", "žízeň", "sette", "sedm"),
                _p("papa", "papež", "pappa", "kaše"),
                _p("fato", "osud", "fatto", "udělaný"),
                _p("capello", "vlas", "cappello", "klobouk"),
            ),
        ),
    ),
    "en": (
        PairSet(
            "i_ee",
            "krátké i nebo dlouhé í",
            "ship má krátké, uvolněné i; sheep dlouhé, napjaté í.",
            (
                _p("ship", "loď", "sheep", "ovce"),
                _p("live", "žít", "leave", "odejít"),
                _p("bit", "kousek", "beat", "porazit"),
                _p("fill", "naplnit", "feel", "cítit"),
            ),
        ),
        PairSet(
            "u_oo",
            "krátké u nebo dlouhé ú",
            "full má krátké uvolněné u; fool dlouhé ú.",
            (
                _p("full", "plný", "fool", "hlupák"),
                _p("pull", "táhnout", "pool", "bazén"),
            ),
        ),
        PairSet(
            "th",
            "th, s nebo f",
            "th: špička jazyka mezi zuby. Ne s, ne f.",
            (
                _p("think", "myslet", "sink", "dřez"),
                _p("thin", "tenký", "fin", "ploutev"),
                _p("three", "tři", "free", "volný"),
                _p("mouth", "ústa", "mouse", "myš"),
            ),
        ),
        PairSet(
            "w_v",
            "w nebo v",
            "w: rty do kroužku, zuby se rtu nedotknou. v: horní zuby na dolním rtu.",
            (
                _p("wine", "víno", "vine", "réva"),
                _p("west", "západ", "vest", "tílko"),
                _p("wet", "mokrý", "vet", "veterinář"),
            ),
        ),
        PairSet(
            "e_ae",
            "e nebo æ",
            "bed má české e; bad otevřenější, mezi e a a.",
            (
                _p("bed", "postel", "bad", "špatný"),
                _p("men", "muži", "man", "muž"),
                _p("pen", "pero", "pan", "pánev"),
            ),
        ),
        PairSet(
            "final",
            "znělá na konci",
            "Čeština znělou souhlásku na konci vysloví neznělou (spodoba), angličtina ne:"
            " bag a back se liší. Před znělou je samohláska delší.",
            (
                _p("bag", "taška", "back", "záda"),
                _p("dog", "pes", "dock", "přístaviště"),
                _p("eyes", "oči", "ice", "led"),
                _p("bed", "postel", "bet", "sázka"),
            ),
        ),
    ),
}


def sets(language: Language) -> tuple[PairSet, ...]:
    return SETS.get(language, ())


def find(language: Language, set_id: str) -> PairSet | None:
    return next((s for s in sets(language) if s.id == set_id), None)
