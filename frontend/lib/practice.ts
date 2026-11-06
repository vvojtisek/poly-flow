// The practice modes outside lessons and checks: shown on the practice hub, the dashboard and
// the mobile tab bar. None of them is graded; the copy lives in cs.practice.

import { BookOpenText, Drama, FlaskConical, Headphones, Shapes, Waves, type LucideIcon } from "lucide-react";

import type { Language } from "@/lib/api";

export type Skill = "listening" | "speaking" | "writing" | "reading" | "grammar";

export interface PracticeMode {
  id: "roleplay" | "dictation" | "shadowing" | "genders" | "cases" | "stories";
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
  { id: "stories", href: "/stories", icon: BookOpenText, skills: ["reading"] },
];

export function modesFor(language: Language): PracticeMode[] {
  return PRACTICE_MODES.filter((m) => !m.languages || m.languages.includes(language));
}
