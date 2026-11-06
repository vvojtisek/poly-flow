"""What's new (Co je nového): learner-facing release notes in Czech. Pure data + selection.

Each entry has a number that only grows; a profile stores the newest number it has seen
(`settings.news_seen`), so the dashboard can say how many entries are new without a table. An
entry limited to some languages (the case lab is German only) is shown only for those.

Append new entries at the end with the next number; never renumber or reuse one, or a profile
would see an old entry as new (or miss a new one).
"""

from dataclasses import dataclass

from app.domain.enums import Language

DE_FR_IT: tuple[Language, ...] = (Language.DE, Language.FR, Language.IT)


@dataclass(frozen=True, slots=True)
class Entry:
    n: int
    date: str  # ISO date the entry was added
    title: str
    blurb: str
    href: str | None
    languages: tuple[Language, ...] | None = None  # None: every language

    def for_language(self, language: Language) -> bool:
        return self.languages is None or language in self.languages


_D = "2026-11-06"

ENTRIES: tuple[Entry, ...] = (
    Entry(1, _D, "Rozřazovací test až po B2+",
          "Krátký přizpůsobivý test najde, kde opravdu jsi, a otevře lekce od té úrovně.",
          "/placement"),
    Entry(2, _D, "Cesta hodností",
          "Osobní cesta, která roste jen s tím, co jsi v Ověření opravdu prokázal."
          " Nikdy ji neztratíš a nikoho s nikým nesrovnává. Dá se skrýt.",
          "/ranks"),
    Entry(3, _D, "Rychlé hledání",
          "Ctrl+K (nebo lupa nahoře) otevře hledání: stránky, slova i nastavení na jednom místě.",
          None),
    Entry(4, _D, "Statistiky",
          "Kalendář učení, přesnost po týdnech, typy chyb a kolik slov čeká na opakování.",
          "/insights"),
    Entry(5, _D, "Můj slovník",
          "Všechna tvá slova s výslovností, stavem a historií odpovědí.",
          "/words"),
    Entry(6, _D, "Plán na dnes",
          "Na úvodní stránce jedno tlačítko na to nejužitečnější, co teď udělat,"
          " a klidný denní cíl.",
          "/"),
    Entry(7, _D, "Diktát",
          "Poslechni si větu, napiš ji a uvidíš, které slovo ti uteklo. Jen procvičování.",
          "/dictation"),
    Entry(8, _D, "Laboratoř pádů",
          "Poskládej členy, přídavné jméno a podstatné jméno a uvidíš, které slovo nese pád.",
          "/grammar/cases", (Language.DE,)),
    Entry(9, _D, "Stínování",
          "Poslechni si větu, zopakuj ji nahlas a porovnej rytmus. Nahrávka nikam neodchází.",
          "/shadowing"),
    Entry(10, _D, "Rody",
          "Třiď podstatná jména klávesami 1-2-3; při chybě uvidíš pravidlo podle koncovky.",
          "/genders", DE_FR_IT),
    Entry(11, _D, "Hraj roli",
          "Zahraj si scénu z lekce za jednoho z mluvčích: vyber nebo napiš svou repliku.",
          "/roleplay"),
    Entry(12, _D, "Procvičování na jednom místě",
          "Všechny způsoby procvičování na jedné stránce; na telefonu lišta dole na palec.",
          "/practice"),
    Entry(13, _D, "Pohodlné čtení",
          "Větší písmo, širší mezery a vypnuté animace pro tvůj profil, na každém zařízení.",
          "/settings"),
    Entry(14, _D, "Oslí můstky",
          "Ke každému slovu si můžeš napsat vlastní poznámku; ukáže se v lekci i po chybě.",
          "/words"),
    Entry(15, _D, "Časování",
          "Přítomný čas všech sloves z tvého slovníku: kmen, koncovka a proč. Nově i ve"
          " francouzštině a italštině.",
          "/grammar/verbs", DE_FR_IT),
    Entry(16, _D, "Rozbor po Ověření",
          "Po Ověření slovo po slovu: tvoje odpověď, správná odpověď a kdy slovo přijde znovu.",
          None),
    Entry(17, _D, "Klepni na slovo",
          "Ve čtení, v Hraj roli a v diktátu klepni na slovo a uvidíš, co znamená.",
          "/stories"),
    Entry(18, _D, "Slovník s sebou",
          "Stáhni si svá slova jako tabulku nebo jako soubor pro Anki.",
          "/words"),
    Entry(19, _D, "Čísla",
          "Čísla od nuly do 9999: napsat slovy, poslechnout, přečíst.",
          "/numbers"),
    Entry(20, _D, "Slovosled",
          "Poskládej rozházená slova zpátky do věty ze scén, které znáš.",
          "/word-order"),
    Entry(21, _D, "Kolik je hodin?",
          "Ručičkové hodiny a jak se čas říká jinde. Pozor na \u201ečtvrt na čtyři\u201c.",
          "/clock"),
    Entry(22, _D, "Barva aplikace",
          "Vyber si jednu z pěti barev tlačítek a zvýraznění."
          " Barvy rodů a správně/špatně zůstávají.",
          "/settings"),
    Entry(23, _D, "Soustředění",
          "V lekci a v Ověření skryje nabídky a nechá jen úkol. Klávesa F.",
          "/lesson"),
    Entry(24, _D, "Jak se to čte",
          "Pravidla výslovnosti pro české oko: ei, sch, ou, gli, th,"
          " s příklady ze slov, která znáš.",
          "/sounds"),
    Entry(25, _D, "Slyšíš rozdíl?",
          "Dvojice slov, která české ucho slyší stejně: ship a sheep, Tür a Tier, pala a palla.",
          "/pairs"),
    Entry(26, _D, "Týden v kostce",
          "Nahoře ve Statistikách: tento týden proti minulému, slova, která zlobila, a co dál.",
          "/insights"),
)  # fmt: skip

LATEST = ENTRIES[-1].n


def for_language(language: Language) -> list[Entry]:
    """Newest first."""
    return [e for e in reversed(ENTRIES) if e.for_language(language)]


def unseen(language: Language, seen: int) -> int:
    return sum(1 for e in ENTRIES if e.n > seen and e.for_language(language))
