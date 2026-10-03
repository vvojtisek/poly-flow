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
  languages: { de: "Němčina", fr: "Francouzština", it: "Italština" },
} as const;
