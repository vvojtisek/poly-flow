// Personal rank path: copy and visuals per theme. The server only knows rank numbers (1-10),
// tiers and requirement keys (backend/app/domain/ranks.py); everything learner-facing is here.

import {
  Award,
  BookOpen,
  Castle,
  Crown,
  Flag,
  Flame,
  Footprints,
  Gem,
  Landmark,
  Medal,
  Scroll,
  Shield,
  ShieldCheck,
  Snowflake,
  Star,
  Swords,
  Trophy,
  Users,
  Wheat,
  type LucideIcon,
} from "lucide-react";

import type { RankPath, RankRequirement, RankTier } from "@/lib/api";

type ThemedPath = Exclude<RankPath, "off">;

export const RANK_NAMES: Record<ThemedPath, string[]> = {
  hockey: [
    "První krůčky na ledě",
    "Jistý bruslař",
    "Žákovská liga",
    "Juniorská liga",
    "Krajský přebor",
    "Extraliga",
    "Play-off",
    "Národní reprezentant",
    "Mistr světa",
    "Olympijský šampion",
  ],
  royal: [
    "Poddaný",
    "Učeň",
    "Páže",
    "Panoš",
    "Zbrojnoš",
    "Rytíř",
    "Rytíř řádu",
    "Hrabě",
    "Vévoda",
    "Král nebo královna jazyka",
  ],
};

export const RANK_ICONS: Record<ThemedPath, LucideIcon[]> = {
  hockey: [Footprints, Snowflake, Users, Shield, Flag, Star, Flame, Award, Trophy, Medal],
  royal: [Wheat, BookOpen, Scroll, Shield, Swords, ShieldCheck, Castle, Landmark, Gem, Crown],
};

export const PATH_NAMES: Record<RankPath, string> = {
  hockey: "Hokejová dráha",
  royal: "Královská cesta",
  off: "Bez hodností",
};

/** Ring gradient and icon colour of the emblem; the frame evolves with the tier. */
export const TIER_STYLE: Record<RankTier, { ring: string; icon: string; label: string }> = {
  bronze: { ring: "from-amber-800 via-orange-500 to-amber-300", icon: "text-amber-700 dark:text-amber-400", label: "bronz" },
  silver: { ring: "from-slate-500 via-slate-300 to-white", icon: "text-slate-500 dark:text-slate-300", label: "stříbro" },
  gold: { ring: "from-yellow-600 via-amber-300 to-yellow-100", icon: "text-yellow-600 dark:text-yellow-400", label: "zlato" },
  platinum: { ring: "from-cyan-600 via-sky-300 to-white", icon: "text-cyan-600 dark:text-cyan-300", label: "platina" },
  diamond: {
    ring: "from-fuchsia-600 via-violet-400 to-sky-300",
    icon: "text-violet-600 dark:text-violet-300",
    label: "diamant",
  },
};

export function rankName(path: RankPath, rank: number): string {
  return RANK_NAMES[path === "off" ? "hockey" : path][rank - 1] ?? "";
}

export function rankIcon(path: RankPath, rank: number): LucideIcon {
  return RANK_ICONS[path === "off" ? "hockey" : path][rank - 1] ?? Star;
}

export function requirementLabel(r: RankRequirement): string {
  switch (r.key) {
    case "known_words":
      return "Ověřená slova (poznáš i napíšeš)";
    case "grammar_known":
      return "Zvládnutá gramatická témata";
    case "recoveries":
      return "Opravené chyby (chyba v ověření, později správně)";
    case "badge":
      return `Zkouška slovní zásoby ${r.level}`;
  }
}

export const ACHIEVEMENT_COPY: Record<string, { title: string; text: string }> = {
  first_word: { title: "První ověřené slovo", text: "Slovo, které poznáš i napíšeš." },
  words_100: { title: "Stovka", text: "100 ověřených slov." },
  words_500: { title: "Pět stovek", text: "500 ověřených slov." },
  words_1000: { title: "Tisícovka", text: "1 000 ověřených slov." },
  passive_250: { title: "Široký rozhled", text: "250 slov, která spolehlivě poznáš." },
  first_rule: { title: "První pravidlo", text: "První gramatické téma zvládnuté v ověření." },
  rules_10: { title: "Gramatik", text: "10 zvládnutých gramatických témat." },
  all_rules: { title: "Mistr gramatiky", text: "Všechna gramatická témata jazyka zvládnutá." },
  recover_1: { title: "Z chyby se učím", text: "První chyba, kterou jsi později opravil(a)." },
  recover_25: { title: "Houževnatost", text: "25 opravených chyb." },
  recover_100: { title: "Nezlomný", text: "100 opravených chyb." },
  badge_a1: { title: "Zkouška A1", text: "Složená zkouška slovní zásoby A1." },
  badge_a2: { title: "Zkouška A2", text: "Složená zkouška slovní zásoby A2." },
  badge_b1: { title: "Zkouška B1", text: "Složená zkouška slovní zásoby B1." },
  badge_b2: { title: "Zkouška B2", text: "Složená zkouška slovní zásoby B2." },
  checks_500: { title: "Vytrvalost", text: "500 odpovědí v ověření." },
  voice_25: { title: "Hlas", text: "25 správných odpovědí nahlas." },
};
