"use client";

import { BookMarked, Dumbbell, Home, Play, Search, type LucideIcon } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { openPalette } from "@/components/CommandPalette";
import { cs } from "@/lib/i18n/cs";

const TABS: { href: string; label: string; icon: LucideIcon; match: (p: string) => boolean }[] = [
  { href: "/", label: cs.tabs.home, icon: Home, match: (p) => p === "/" },
  { href: "/lesson", label: cs.tabs.lesson, icon: Play, match: (p) => p.startsWith("/lesson") || p.startsWith("/check") },
  {
    href: "/practice",
    label: cs.tabs.practice,
    icon: Dumbbell,
    match: (p) => ["/practice", "/dictation", "/shadowing", "/roleplay", "/genders", "/stories", "/grammar/cases"].some((x) => p.startsWith(x)),
  },
  { href: "/words", label: cs.tabs.words, icon: BookMarked, match: (p) => p.startsWith("/words") },
];

/** Thumb-reach navigation on phones; the header carries the same links from lg up. */
export function BottomTabs() {
  const path = usePathname() ?? "/";
  return (
    <nav
      aria-label={cs.tabs.label}
      className="fixed inset-x-0 bottom-0 z-30 border-t border-slate-200 bg-white/95 pb-[env(safe-area-inset-bottom)] backdrop-blur lg:hidden dark:border-slate-800 dark:bg-slate-950/95"
    >
      <ul className="mx-auto grid max-w-lg grid-cols-5">
        {TABS.map((tab) => {
          const active = tab.match(path);
          return (
            <li key={tab.href}>
              <Link
                href={tab.href}
                aria-current={active ? "page" : undefined}
                className={`flex flex-col items-center gap-0.5 py-2 text-[11px] font-medium ${
                  active ? "text-brand-600 dark:text-brand-50" : "text-slate-500 dark:text-slate-400"
                }`}
              >
                <tab.icon className={`size-5 ${active ? "stroke-[2.5]" : ""}`} aria-hidden />
                {tab.label}
              </Link>
            </li>
          );
        })}
        <li>
          <button type="button" onClick={openPalette} className="flex w-full flex-col items-center gap-0.5 py-2 text-[11px] font-medium text-slate-500 dark:text-slate-400">
            <Search className="size-5" aria-hidden />
            {cs.tabs.search}
          </button>
        </li>
      </ul>
    </nav>
  );
}
