// The practice modes outside lessons and checks: shown on the practice hub, the dashboard and
// the mobile tab bar. None of them is graded; the copy lives in cs.practice.

import { AlarmClock, ArrowDownUp, AudioLines, BookOpenText, Ear, Drama, FlaskConical, Hash, Headphones, Repeat, Shapes, Waves, type LucideIcon } from "lucide-react";

import type { Language } from "@/lib/api";

export type Skill = "listening" | "speaking" | "writing" | "reading" | "grammar";

export interface PracticeMode {
  id: "roleplay" | "dictation" | "shadowing" | "genders" | "cases" | "verbs" | "wordOrder" | "numbers" | "clock" | "sounds" | "pairs" | "stories";
  href: string;
  icon: LucideIcon;
  skills: Skill[];
  languages?: Language[]; // only these languages; all when absent
}

export const PRACTICE_MODES: PracticeMode[] = [
  { id: "roleplay", href: "/roleplay", icon: Drama, skills: ["reading", "writing", "listening"] },
  { id: "dictation", href: "/dictation", icon: Headphones, skills: ["listening", "writing"] },
  { id: "shadowing", href: "/shadowing", icon: Waves, skills: ["listening", "speaking"] },
  { id: "genders", href: "/genders", icon: Shapes, skills: ["grammar"], languages: ["de", "fr", "it"] },
  { id: "cases", href: "/grammar/cases", icon: FlaskConical, skills: ["grammar"], languages: ["de"] },
  { id: "verbs", href: "/grammar/verbs", icon: Repeat, skills: ["grammar", "writing"], languages: ["de"] },
  { id: "wordOrder", href: "/word-order", icon: ArrowDownUp, skills: ["grammar", "reading"] },
  { id: "numbers", href: "/numbers", icon: Hash, skills: ["listening", "writing", "reading"] },
  { id: "clock", href: "/clock", icon: AlarmClock, skills: ["reading", "listening"] },
  { id: "sounds", href: "/sounds", icon: AudioLines, skills: ["speaking", "reading"] },
  { id: "pairs", href: "/pairs", icon: Ear, skills: ["listening"] },
  { id: "stories", href: "/stories", icon: BookOpenText, skills: ["reading"] },
];

export function modesFor(language: Language): PracticeMode[] {
  return PRACTICE_MODES.filter((m) => !m.languages || m.languages.includes(language));
}

export const SKILLS: Skill[] = ["listening", "speaking", "writing", "reading", "grammar"];

// The last practice modes this device opened (most recent first). A convenience only: it stays
// in this browser, is never sent to the server and never counts as progress.
const RECENT_KEY = "pf_recent_modes";
const MAX_RECENT = 3;

export function readRecent(): PracticeMode["id"][] {
  try {
    const raw = JSON.parse(window.localStorage.getItem(RECENT_KEY) ?? "[]");
    const ids = new Set(PRACTICE_MODES.map((m) => m.id));
    return Array.isArray(raw) ? raw.filter((x): x is PracticeMode["id"] => ids.has(x)).slice(0, MAX_RECENT) : [];
  } catch {
    return [];
  }
}

/** Remembers a visit when `path` is a practice mode's page. */
export function recordVisit(path: string) {
  const mode = PRACTICE_MODES.find((m) => path === m.href || path.startsWith(`${m.href}/`));
  if (!mode) return;
  try {
    const next = [mode.id, ...readRecent().filter((id) => id !== mode.id)].slice(0, MAX_RECENT);
    window.localStorage.setItem(RECENT_KEY, JSON.stringify(next));
  } catch {
    /* storage unavailable */
  }
}

/** Modes for a language with the recently used ones first (stable order otherwise). */
export function byRecent(modes: PracticeMode[], recent: PracticeMode["id"][]): PracticeMode[] {
  const rank = (m: PracticeMode) => {
    const i = recent.indexOf(m.id);
    return i === -1 ? recent.length : i;
  };
  return [...modes].sort((a, b) => rank(a) - rank(b));
}
