"""French and Italian present tense (présent, presente): rules plus the irregular verbs. Pure.

French: regular -er verbs with their spelling changes (nous commençons, nous mangeons,
j'achète, je préfère, j'appelle, je paie / j'envoie), -ir verbs with -iss- (finir), the
partir, ouvrir and conduire patterns, regular -dre verbs (vendre), and the common irregular
verbs listed whole, found also through a prefix (comprendre, revenir, permettre). "je" becomes
"j'" before a vowel or mute h.

Italian: -are, -ere, -ire, the -isc- verbs (finire, capire), the h kept before i in -care and
-gare (cerchi, paghiamo), one i in -iare (mangi, studiamo), and the common irregular verbs.

A verb outside the lists follows the regular pattern of its ending. The lists cover the common
verbs; the UI says the forms are built by rules, as for German.
"""

import re
from dataclasses import dataclass
from typing import Literal

Lang = Literal["fr", "it"]

PRONOUNS: dict[Lang, tuple[str, ...]] = {
    "fr": ("je", "tu", "il/elle", "nous", "vous", "ils/elles"),
    "it": ("io", "tu", "lui/lei", "noi", "voi", "loro"),
}


@dataclass(frozen=True, slots=True)
class RForm:
    pronoun: str
    stem: str
    ending: str
    changed: bool  # irregular, or the stem's spelling changed


# fmt: off
_FR_WHOLE: dict[str, tuple[str, str, str, str, str, str]] = {
    "être": ("suis", "es", "est", "sommes", "êtes", "sont"),
    "avoir": ("ai", "as", "a", "avons", "avez", "ont"),
    "aller": ("vais", "vas", "va", "allons", "allez", "vont"),
    "faire": ("fais", "fais", "fait", "faisons", "faites", "font"),
    "pouvoir": ("peux", "peux", "peut", "pouvons", "pouvez", "peuvent"),
    "vouloir": ("veux", "veux", "veut", "voulons", "voulez", "veulent"),
    "devoir": ("dois", "dois", "doit", "devons", "devez", "doivent"),
    "savoir": ("sais", "sais", "sait", "savons", "savez", "savent"),
    "venir": ("viens", "viens", "vient", "venons", "venez", "viennent"),
    "tenir": ("tiens", "tiens", "tient", "tenons", "tenez", "tiennent"),
    "prendre": ("prends", "prends", "prend", "prenons", "prenez", "prennent"),
    "mettre": ("mets", "mets", "met", "mettons", "mettez", "mettent"),
    "dire": ("dis", "dis", "dit", "disons", "dites", "disent"),
    "voir": ("vois", "vois", "voit", "voyons", "voyez", "voient"),
    "croire": ("crois", "crois", "croit", "croyons", "croyez", "croient"),
    "boire": ("bois", "bois", "boit", "buvons", "buvez", "boivent"),
    "écrire": ("écris", "écris", "écrit", "écrivons", "écrivez", "écrivent"),
    "lire": ("lis", "lis", "lit", "lisons", "lisez", "lisent"),
    "connaître": ("connais", "connais", "connaît", "connaissons", "connaissez", "connaissent"),
    "vivre": ("vis", "vis", "vit", "vivons", "vivez", "vivent"),
    "recevoir": ("reçois", "reçois", "reçoit", "recevons", "recevez", "reçoivent"),
    "courir": ("cours", "cours", "court", "courons", "courez", "courent"),
}
# Prefixed forms that conjugate like their base (comprendre like prendre).
_FR_PREFIXED = {
    "prendre": ("ap", "com", "re", "sur", "entre"),
    "venir": ("re", "de", "pré", "sou", "con", "inter"),
    "tenir": ("ob", "re", "con", "main", "ap", "sou"),
    "mettre": ("per", "pro", "re", "ad", "sou", "com"),
    "écrire": ("d", "ins", "pres"),  # décrire, inscrire, prescrire
    "voir": ("re", "pré"),
    "faire": ("re", "dé", "satis"),
    "connaître": ("re",),
}
_FR_PARTIR = {"partir", "sortir", "dormir", "servir", "sentir", "mentir", "repartir", "ressentir"}
_FR_OUVRIR = {"ouvrir", "offrir", "couvrir", "découvrir", "souffrir", "rouvrir"}
_FR_DOUBLE = {"appeler", "rappeler", "jeter", "rejeter", "épeler", "renouveler"}  # j'appelle
_FR_GRAVE = {"acheter", "lever", "mener", "amener", "emmener", "promener", "peser", "geler",
             "élever", "enlever", "achever"}  # j'achète

_IT_WHOLE: dict[str, tuple[str, str, str, str, str, str]] = {
    "essere": ("sono", "sei", "è", "siamo", "siete", "sono"),
    "avere": ("ho", "hai", "ha", "abbiamo", "avete", "hanno"),
    "fare": ("faccio", "fai", "fa", "facciamo", "fate", "fanno"),
    "andare": ("vado", "vai", "va", "andiamo", "andate", "vanno"),
    "potere": ("posso", "puoi", "può", "possiamo", "potete", "possono"),
    "volere": ("voglio", "vuoi", "vuole", "vogliamo", "volete", "vogliono"),
    "dovere": ("devo", "devi", "deve", "dobbiamo", "dovete", "devono"),
    "sapere": ("so", "sai", "sa", "sappiamo", "sapete", "sanno"),
    "dire": ("dico", "dici", "dice", "diciamo", "dite", "dicono"),
    "venire": ("vengo", "vieni", "viene", "veniamo", "venite", "vengono"),
    "dare": ("do", "dai", "dà", "diamo", "date", "danno"),
    "stare": ("sto", "stai", "sta", "stiamo", "state", "stanno"),
    "bere": ("bevo", "bevi", "beve", "beviamo", "bevete", "bevono"),
    "uscire": ("esco", "esci", "esce", "usciamo", "uscite", "escono"),
    "tenere": ("tengo", "tieni", "tiene", "teniamo", "tenete", "tengono"),
    "rimanere": ("rimango", "rimani", "rimane", "rimaniamo", "rimanete", "rimangono"),
    "scegliere": ("scelgo", "scegli", "sceglie", "scegliamo", "scegliete", "scelgono"),
    "salire": ("salgo", "sali", "sale", "saliamo", "salite", "salgono"),
    "tradurre": ("traduco", "traduci", "traduce", "traduciamo", "traducete", "traducono"),
    "morire": ("muoio", "muori", "muore", "moriamo", "morite", "muoiono"),
    "sedere": ("siedo", "siedi", "siede", "sediamo", "sedete", "siedono"),
    "piacere": ("piaccio", "piaci", "piace", "piacciamo", "piacete", "piacciono"),
}
_IT_PREFIXED = {"tenere": ("ot", "man", "con", "ri", "so", "ap"), "venire": ("di", "con", "av")}
_IT_ISC = {"finire", "capire", "preferire", "pulire", "spedire", "costruire", "restituire",
           "sparire", "suggerire", "tradire", "unire", "colpire", "gestire", "guarire",
           "impedire", "inserire", "obbedire", "proibire", "reagire", "riferire", "sostituire",
           "stabilire", "trasferire", "favorire", "fornire", "garantire", "chiarire"}
_IT_STRESSED_I = {"sciare", "inviare", "avviare", "spiare"}  # tu scii, tu invii
# fmt: on

_FR_ENDINGS = {
    "er": ("e", "es", "e", "ons", "ez", "ent"),
    "ir": ("is", "is", "it", "issons", "issez", "issent"),
    "re": ("s", "s", "", "ons", "ez", "ent"),
    "partir": ("s", "s", "t", "ons", "ez", "ent"),
    "uire": ("s", "s", "t", "sons", "sez", "sent"),  # je conduis, nous conduisons
}
_IT_ENDINGS = {
    "are": ("o", "i", "a", "iamo", "ate", "ano"),
    "ere": ("o", "i", "e", "iamo", "ete", "ono"),
    "ire": ("o", "i", "e", "iamo", "ite", "ono"),
    "isc": ("isco", "isci", "isce", "iamo", "ite", "iscono"),
}
_VOWELS = "aeiouyàâéèêëîïôûùœh"


def _whole(verb: str, table: dict, prefixed: dict) -> tuple[str, tuple[str, ...]] | None:
    """(prefix, forms of the base) for a listed verb or a prefixed one (comprendre)."""
    if verb in table:
        return "", table[verb]
    for base, prefixes in prefixed.items():
        for p in prefixes:
            if verb == p + base:
                return p, table[base]
    return None


def _fr_pronouns(forms: list[str]) -> list[str]:
    out = list(PRONOUNS["fr"])
    if forms[0][:1].lower() in _VOWELS:
        out[0] = "j'"
    return out


def conjugate_fr(infinitive: str) -> list[RForm]:
    verb = infinitive.strip().lower()
    found = _whole(verb, _FR_WHOLE, _FR_PREFIXED)
    if found:
        prefix, forms = found
        texts = [prefix + f for f in forms]
        return [RForm(p, t, "", True) for p, t in zip(_fr_pronouns(texts), texts, strict=True)]
    if verb in _FR_OUVRIR:
        stem = verb[:-2]
        ends = _FR_ENDINGS["er"]
        stems = [stem] * 6
        changed = [False] * 6
    elif verb in _FR_PARTIR:
        full = verb[:-2]  # dorm, part, sort
        short = full[:-1]  # dor, par, sor
        ends = _FR_ENDINGS["partir"]
        stems = [short, short, short, full, full, full]
        changed = [True, True, True, False, False, False]
    elif verb.endswith("er"):
        stem = verb[:-2]
        ends = _FR_ENDINGS["er"]
        stems = [stem] * 6
        changed = [False] * 6
        boot = (0, 1, 2, 5)  # je, tu, il, ils: the stressed stem
        if stem.endswith("c"):
            stems[3] = stem[:-1] + "ç"  # nous commençons
            changed[3] = True
        elif stem.endswith("g"):
            stems[3] = stem + "e"  # nous mangeons
            changed[3] = True
        if verb in _FR_DOUBLE:
            for i in boot:
                stems[i] = stem + stem[-1]  # j'appelle, je jette
                changed[i] = True
        elif verb in _FR_GRAVE:
            k = stem.rfind("e")
            for i in boot:
                stems[i] = stem[:k] + "è" + stem[k + 1 :]  # j'achète
                changed[i] = True
        elif m := re.search(r"é[^aeiouyéèê]+$", stem):
            k = m.start()
            for i in boot:
                stems[i] = stem[:k] + "è" + stem[k + 1 :]  # je préfère
                changed[i] = True
        if stem.endswith("y"):
            for i in boot:
                stems[i] = stem[:-1] + "i"  # je paie, j'envoie
                changed[i] = True
    elif verb.endswith("uire"):
        stem = verb[:-2]  # condui, tradui, constru-i
        ends = _FR_ENDINGS["uire"]
        stems = [stem] * 6
        changed = [False, False, False, True, True, True]
    elif verb.endswith("ir"):
        stem = verb[:-2]
        ends = _FR_ENDINGS["ir"]
        stems = [stem] * 6
        changed = [False] * 6
    elif verb.endswith("re"):
        stem = verb[:-2]
        ends = _FR_ENDINGS["re"]
        stems = [stem] * 6
        changed = [False] * 6
    else:
        raise ValueError(f"not a French infinitive: {infinitive}")
    texts = [s + e for s, e in zip(stems, ends, strict=True)]
    pronouns = _fr_pronouns(texts)
    return [RForm(p, s, e, c) for p, s, e, c in zip(pronouns, stems, ends, changed, strict=True)]


def conjugate_it(infinitive: str) -> list[RForm]:
    verb = infinitive.strip().lower()
    pron = PRONOUNS["it"]
    found = _whole(verb, _IT_WHOLE, _IT_PREFIXED)
    if found:
        prefix, forms = found
        return [RForm(p, prefix + f, "", True) for p, f in zip(pron, forms, strict=True)]
    if verb.endswith("are"):
        kind = "are"
    elif verb.endswith("ere"):
        kind = "ere"
    elif verb.endswith("ire"):
        kind = "isc" if verb in _IT_ISC else "ire"
    else:
        raise ValueError(f"not an Italian infinitive: {infinitive}")
    stem = verb[:-3]
    ends = list(_IT_ENDINGS[kind])
    stems = [stem] * 6
    changed = [False] * 6
    if kind == "are" and stem.endswith(("c", "g")):
        for i in (1, 3):  # tu cerchi, noi cerchiamo: keep the hard sound
            stems[i] = stem + "h"
            changed[i] = True
    if stem.endswith("i"):
        # noi mangiamo: one i, not two; tu mangi too, unless the i is stressed (tu invii).
        for i in (3,) if verb in _IT_STRESSED_I else (1, 3):
            ends[i] = ends[i][1:]
            changed[i] = True
    return [RForm(p, s, e, c) for p, s, e, c in zip(pron, stems, ends, changed, strict=True)]


Feature = Literal[
    "irregular", "fr_er", "fr_ir", "fr_re", "fr_partir", "fr_ouvrir", "fr_uire", "spelling",
    "elision",
    "it_are", "it_ere", "it_ire", "it_isc", "it_h", "it_i",
]  # fmt: skip


def features(infinitive: str, language: Lang) -> list[Feature]:
    verb = infinitive.strip().lower()
    out: list[Feature] = []
    if language == "fr":
        forms = conjugate_fr(verb)
        if _whole(verb, _FR_WHOLE, _FR_PREFIXED):
            out.append("irregular")
        elif verb in _FR_OUVRIR:
            out.append("fr_ouvrir")
        elif verb in _FR_PARTIR:
            out.append("fr_partir")
        elif verb.endswith("er"):
            out.append("fr_er")
            if any(f.changed for f in forms):
                out.append("spelling")
        elif verb.endswith("ir"):
            out.append("fr_ir")
        elif verb.endswith("uire"):
            out.append("fr_uire")
        else:
            out.append("fr_re")
        if forms[0].pronoun == "j'":
            out.append("elision")
        return out
    forms = conjugate_it(verb)
    if _whole(verb, _IT_WHOLE, _IT_PREFIXED):
        return ["irregular"]
    out.append("it_isc" if verb in _IT_ISC else ("it_" + verb[-3:]))  # type: ignore[arg-type]
    if forms[1].stem.endswith("h"):
        out.append("it_h")
    if forms[3].ending == "amo":
        out.append("it_i")
    return out
