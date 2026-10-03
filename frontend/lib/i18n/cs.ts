// cs-CZ UI strings. All user-facing copy goes through this table.
export const cs = {
  appName: "PolyFlow",
  tagline: "Rodinná jazyková škola – němčina, francouzština, italština",
  todayPractice: "Dnešní procvičování",
  startDrill: "Začít procvičovat",
  comingSoon: "Připravujeme",
  dashboard: {
    title: "Přehled",
    vocabularyCoverage: "Pokrytí slovní zásoby",
    retention: "Vývoj zapomínání",
    streak: "Série dní",
    serverHealth: "Stav serveru",
  },
  health: {
    ready: "Vše funguje",
    unready: "Některé služby nejsou dostupné",
    unreachable: "Server je nedostupný",
    checking: "Ověřuji…",
    services: { postgres: "Databáze", redis: "Fronta úloh" } as Record<string, string>,
  },
  progression: {
    title: "Tvoje cesta",
    words: "slov",
    milestones: {
      core_100: "Prvních 100 slov",
      basic_500: "Základ",
      a2: "A2",
      b1: "B1",
      b2_threshold: "Práh B2",
      b2_full: "Plné B2",
      extension_passive: "Pasivní slovní zásoba – dobrovolné",
    } as Record<string, string>,
    voluntaryBadge: "dobrovolné",
    beyondB2:
      "Plným B2 (5 000 slov) povinná část končí. Pokud chceš, můžeš se dál učit nová slova – hlavně kvůli porozumění při čtení a poslechu. Úroveň C1 ale aplikace nedá: přichází z reálného používání jazyka – z rozhovorů s lidmi, knih, filmů a kultury.",
    cefrDisclaimer:
      "Úrovně CEFR jsou orientační. Počet slov je jen jedna složka jazykové úrovně.",
    unavailable: "Nepodařilo se načíst postup.",
  },
  languages: { de: "Němčina", fr: "Francouzština", it: "Italština" },
} as const;
