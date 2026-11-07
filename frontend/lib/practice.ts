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
  needsWords?: boolean; // builds on words or scenes the learner has met in lessons
}

export const PRACTICE_MODES: PracticeMode[] = [
  { id: "roleplay", needsWords: true, href: "/roleplay", icon: Drama, skills: ["reading", "writing", "listening"] },
  { id: "dictation", needsWords: true, href: "/dictation", icon: Headphones, skills: ["listening", "writing"] },
  { id: "shadowing", needsWords: true, href: "/shadowing", icon: Waves, skills: ["listening", "speaking"] },
  { id: "genders", href: "/genders", icon: Shapes, skills: ["grammar"], languages: ["de", "fr", "it"] },
  { id: "cases", href: "/grammar/cases", icon: FlaskConical, skills: ["grammar"], languages: ["de"] },
  { id: "verbs", href: "/grammar/verbs", icon: Repeat, skills: ["grammar", "writing"], languages: ["de", "fr", "it"] },
  { id: "wordOrder", needsWords: true, href: "/word-order", icon: ArrowDownUp, skills: ["grammar", "reading"] },
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
const PINNED_KEY = "pf_pinned_modes";
const MAX_RECENT = 3;

export function readPinned(): PracticeMode["id"][] {
  try {
    const raw = JSON.parse(window.localStorage.getItem(PINNED_KEY) ?? "[]");
    const ids = new Set(PRACTICE_MODES.map((m) => m.id));
    return Array.isArray(raw) ? [...new Set(raw.filter((x): x is PracticeMode["id"] => ids.has(x)))] : [];
  } catch {
    return [];
  }
}

export function togglePinned(id: PracticeMode["id"]): PracticeMode["id"][] {
  const current = readPinned();
  const next = current.includes(id) ? current.filter((item) => item !== id) : [...current, id];
  try {
    window.localStorage.setItem(PINNED_KEY, JSON.stringify(next));
  } catch {
    /* storage unavailable */
  }
  return next;
}

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
    window.localStorage.setItem(VISITS_KEY, JSON.stringify({ ...readVisits(), [mode.id]: new Date().toISOString() }));
  } catch {
    /* storage unavailable */
  }
}

// When each mode was last opened on this device (ISO time). Like the recent list, a local
// convenience for choosing what to do; it is not a record of learning.
const VISITS_KEY = "pf_mode_visits";

export function readVisits(): Partial<Record<PracticeMode["id"], string>> {
  try {
    const raw = JSON.parse(window.localStorage.getItem(VISITS_KEY) ?? "{}");
    if (!raw || typeof raw !== "object" || Array.isArray(raw)) return {};
    const ids = new Set<string>(PRACTICE_MODES.map((m) => m.id));
    return Object.fromEntries(
      Object.entries(raw).filter(([k, v]) => ids.has(k) && typeof v === "string" && !Number.isNaN(Date.parse(v))),
    ) as Partial<Record<PracticeMode["id"], string>>;
  } catch {
    return {};
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

/**
 * Suggestions for today, best first: skills ordered by how long ago they were trained on this
 * device (never first), each with its least recently opened mode, then the remaining modes by age.
 * Deterministic, so the tip does not change on every visit.
 */
export function suggestModes(
  modes: PracticeMode[],
  visits: Partial<Record<PracticeMode["id"], string>>,
  usable: (m: PracticeMode) => boolean = () => true,
): { mode: PracticeMode; skill: Skill; since: string | null }[] {
  const pool = modes.filter(usable);
  const at = (m: PracticeMode) => (visits[m.id] ? Date.parse(visits[m.id]!) : 0);
  const lastFor = (s: Skill) => Math.max(0, ...pool.filter((m) => m.skills.includes(s)).map(at));
  const skills = SKILLS.filter((s) => pool.some((m) => m.skills.includes(s))).sort(
    (a, b) => lastFor(a) - lastFor(b) || SKILLS.indexOf(a) - SKILLS.indexOf(b),
  );
  const out: { mode: PracticeMode; skill: Skill; since: string | null }[] = [];
  const taken = new Set<string>();
  const byAge = (a: PracticeMode, b: PracticeMode) => at(a) - at(b) || pool.indexOf(a) - pool.indexOf(b);
  for (const skill of skills) {
    const mode = pool.filter((m) => m.skills.includes(skill) && !taken.has(m.id)).sort(byAge)[0];
    if (!mode) continue;
    taken.add(mode.id);
    const last = lastFor(skill);
    out.push({ mode, skill, since: last ? new Date(last).toISOString() : null });
  }
  for (const mode of pool.filter((m) => !taken.has(m.id)).sort(byAge)) {
    const skill = mode.skills[0]!;
    const last = at(mode);
    out.push({ mode, skill, since: last ? new Date(last).toISOString() : null });
  }
  return out;
}
