"""How letters sound: spelling-to-sound rules for a Czech reader, per language. Pure data + match.

Czech is read almost letter by letter, so the first reflex of a Czech learner is to read "ei" as
e-i or "ou" as o-u. Each rule names a spelling, the nearest Czech sound (or says there is none)
and a short note; examples come from the lexicon at request time, so the learner hears words
they know.

These rules are simplified (drafted, not yet reviewed by a native speaker); "usually" marks rules
with common exceptions. Patterns are deliberately conservative: a word that matches should show
the rule, even if some words that follow the rule are not matched.
"""

import re
from dataclasses import dataclass

from app.domain.enums import Language


@dataclass(frozen=True, slots=True)
class Rule:
    id: str
    spelling: str  # as shown: "ei, ai"
    czech: str  # nearest Czech sound, in Czech letters, or a description
    note: str  # one line of Czech explanation
    pattern: str  # regex over the lowercase lemma; group 1 (or the match) is highlighted

    def find(self, word: str) -> tuple[int, int] | None:
        m = re.search(self.pattern, word)
        if not m:
            return None
        for i, g in enumerate(m.groups(), start=1):
            if g is not None:
                return m.span(i)
        return m.span()


RULES: dict[Language, tuple[Rule, ...]] = {
    "de": (
        Rule("ei", "ei, ai", "aj", "Dvojhláska: mein = majn, Mai = maj.", r"(ei|ai)"),
        Rule("eu", "eu, äu", "oj", "Dvojhláska: heute = hojte, Häuser = hojzr.", r"(eu|äu)(?!m$)"),
        Rule("ie", "ie", "í", "Dlouhé í, žádné i-e: Liebe = líbe.", r"(ie)(?!n$)"),
        Rule("sch", "sch", "š", "Tři písmena, jedna hláska: Schule = šúle.", r"(?<!t)(sch)"),
        Rule("tsch", "tsch", "č", "Deutsch = dojč.", r"(tsch)"),
        Rule(
            "st",
            "st-, sp- na začátku",
            "št, šp",
            "Na začátku slova (i po předponě): Stadt = štat, spielen = špílen.",
            r"^(st|sp)",
        ),
        Rule(
            "ch_hard",
            "ch po a, o, u, au",
            "ch",
            "Jako české ch: Buch, auch, noch.",
            r"(?<![eä])(?:a|o|u)(ch)",
        ),
        Rule(
            "ch_soft",
            "ch po e, i, ä, ö, ü, eu, l, n, r",
            "měkké ch",
            "Česky ho nemáme: něco mezi ch a š, jazyk u horních zubů: ich, Milch.",
            r"(?:[eiäöülnr]|eu|äu)(ch)(?!s)",
        ),
        Rule("z", "z, tz", "c", "Zeit = cajt, jetzt = jecst.", r"(tz|z)"),
        Rule(
            "v",
            "v",
            "f (obvykle)",
            "Vater = fátr, viel = fíl. Ve slovech z cizích jazyků v: Klavier.",
            r"^(v)",
        ),
        Rule("w", "w", "v", "Wasser = vasr, wo = vó.", r"(w)"),
        Rule(
            "s",
            "s před samohláskou",
            "z (obvykle)",
            "Sonne = zone, lesen = lézen.",
            r"(?:^|[aeiouäöü])(s)[aeiouäöü]",
        ),
        Rule("ss", "ß", "s", "Ostré s po dlouhé samohlásce: heißen, Straße.", r"(ß)"),
        Rule("umlaut_a", "ä", "e", "Mädchen = métchen.", r"(ä)"),
        Rule(
            "umlaut_o",
            "ö",
            "e se zaokrouhlenými rty",
            "Řekni e a zaokrouhli rty jako na o: schön.",
            r"(ö)",
        ),
        Rule(
            "umlaut_u",
            "ü",
            "i se zaokrouhlenými rty",
            "Řekni i a zaokrouhli rty jako na u: müde, für.",
            r"(ü)",
        ),
        Rule(
            "h",
            "h po samohlásce",
            "obvykle se nevyslovuje",
            "Jen prodlužuje samohlásku: gehen = géen, Uhr = úr. Ne na začátku části slova: woher.",
            r"[aeiouäöü](h)",
        ),
        Rule(
            "er",
            "-er na konci",
            "slabé a",
            "Lehrer = lérɐ, Vater = fátɐ: r se skoro neozve.",
            r"(er)$",
        ),
        Rule("qu", "qu", "kv", "Quelle = kvele.", r"(qu)"),
    ),
    "fr": (
        Rule("ou", "ou", "u", "Jedna hláska: vous = vu, rouge = rúž.", r"(ou)"),
        Rule("oi", "oi", "wa (ua)", "moi = mwa, trois = trwa.", r"(oi)"),
        Rule("au", "au, eau", "o", "eau = ó, beau = bó, aussi = osi.", r"(eau|au)"),
        Rule("ai", "ai, ei", "e (otevřené)", "lait = le, maison = mezon.", r"(ai|ei)(?!n)"),
        Rule(
            "eu", "eu, œu", "e se zaokrouhlenými rty", "deux, sœur: e se rty jako na o.", r"(œu|eu)"
        ),
        Rule(
            "u",
            "u",
            "i se zaokrouhlenými rty",
            "tu, rue: ne české u.",
            r"(?<![aeoq])(u)(?![ia]|[nm](?:[^aeiouy]|$))",
        ),
        Rule(
            "on",
            "on, om",
            "nosové o",
            "bon, nom: vzduch jde i nosem, n se nevyslovuje.",
            r"(on|om)(?![aeiouynm])",
        ),
        Rule(
            "an",
            "an, en, am, em",
            "nosové a",
            "enfant, temps: nosové a, n se nevyslovuje.",
            r"(an|am|em|(?<![ié])en)(?![aeiouynm])",
        ),
        Rule(
            "in",
            "in, ain, ein, ien, im",
            "nosové e",
            "vin, pain, plein, bien.",
            r"(ain|ein|ien|in|im)(?![aeiouynm])",
        ),
        Rule("ch", "ch", "š", "chat = ša, chez = še.", r"(ch)"),
        Rule("gn", "gn", "ň", "montagne = montaň.", r"(gn)"),
        Rule("qu", "qu", "k", "qui = ki, quatre = katr.", r"(qu)"),
        Rule(
            "j", "j, g před e, i", "ž", "je = že, rouge = rúž, manger = manže.", r"(j)|(g)(?=[eiy])"
        ),
        Rule("c", "c před e, i; ç", "s", "merci = mersi, ça = sa.", r"(ç)|(c)(?=[eiy])"),
        Rule(
            "ill",
            "ill po samohlásce, -ille",
            "j (obvykle)",
            "fille = fij, travailler. Výjimky: ville, mille.",
            r"[aeiou](ill)|(?<![vm])(ill)e$",
        ),
        Rule("h", "h", "nevyslovuje se", "homme = om, hôtel = otel.", r"^(h)"),
        Rule(
            "final",
            "souhláska na konci",
            "obvykle tichá",
            "petit = peti, vous = vu. Často se ozve c, r, f, l (avec, mer).",
            r"[aeiouéèê]([dtsxzp])$",
        ),
    ),
    "it": (
        Rule("ce", "c před e, i", "č", "cena = čena, ciao = čao.", r"(?<!s)(c)(?=[ei])"),
        Rule("che", "ch", "k", "che = ke, chi = ki.", r"(ch)"),
        Rule("ge", "g před e, i", "dž", "gelato = dželato, giorno = džorno.", r"(g)(?=[ei])"),
        Rule("ghe", "gh", "g", "spaghetti, ghiaccio.", r"(gh)"),
        Rule("gli", "gli", "ľ (měkké l)", "figlio = fiľo, famiglia.", r"(gli)"),
        Rule("gn", "gn", "ň", "bagno = baňo, sogno.", r"(gn)"),
        Rule("sce", "sc před e, i", "š", "scena = šena, uscire.", r"(sc)(?=[ei])"),
        Rule("z", "z, zz", "c (někdy dz)", "pizza = picca, zero = dzero.", r"(zz|z)"),
        Rule(
            "double",
            "zdvojená souhláska",
            "vyslov déle",
            "notte, anno, piccolo: souhláska se drží déle, mění význam (pala a palla).",
            r"(([bcdfglmnprstvz])\2)",
        ),
        Rule("h", "h", "nevyslovuje se", "ho = o, hanno = anno.", r"^(h)"),
    ),
    "en": (
        Rule(
            "th",
            "th",
            "česky nemáme",
            "Špička jazyka mezi zuby: think (neznělé), this (znělé). Ne t, ne f.",
            r"(th)",
        ),
        Rule("w", "w", "krátké u", "water: rty do kroužku, ne české v.", r"^(w)(?!r|ho)"),
        Rule("sh", "sh", "š", "she, wish.", r"(sh)"),
        Rule(
            "ch",
            "ch, tch",
            "č (obvykle)",
            "child, watch. Výjimky: school, character (k).",
            r"(?<!s)(tch|ch)",
        ),
        Rule("j", "j", "dž", "job, just.", r"^(j)"),
        Rule(
            "ee",
            "ee, ea",
            "í (obvykle)",
            "see, tea, speak. Jinak: year, head, great.",
            r"(ee|ea)(?![rd])",
        ),
        Rule(
            "oo",
            "oo",
            "ú (obvykle)",
            "food, school, soon. Krátké u: book, good, look.",
            r"(oo)(?!k|r|d$)",
        ),
        Rule(
            "ou",
            "ou",
            "au (obvykle)",
            "house, out, round. Výjimky: you, group, country.",
            r"(ou)(?=t|nd|se)",
        ),
        Rule("tion", "-tion", "šn", "nation = nejšn, station.", r"(tion)"),
        Rule("igh", "igh", "aj", "night, high.", r"(igh)"),
        Rule("kn", "kn-, wr-", "k, w se nevyslovují", "know = nou, write = rajt.", r"^(kn|wr)"),
        Rule(
            "r",
            "r po samohlásce",
            "britsky tiché",
            "car = ká, hard = hád: r se v britské výslovnosti neozve.",
            r"[aeiou](r)(?![aeiouyr])",
        ),
        Rule(
            "e",
            "-e na konci",
            "tiché",
            "make, time: e se nečte a samohláska před ním se často čte jako svůj název (ej, aj).",
            r"[aeiouy][^aeiouy](e)$",
        ),
        Rule("y", "-y na konci", "i", "happy, city.", r"[aeiou][^aeiouy]+(y)$"),
    ),
}


def rules(language: Language) -> tuple[Rule, ...]:
    return RULES.get(language, ())
