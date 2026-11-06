"use client";

import { ArrowRight, BookOpen, BookOpenText, ClipboardCheck, GraduationCap, type LucideIcon } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { KeyHint } from "@/components/Kbd";
import { Button } from "@/components/ui";
import { getToday, listStoryArchive, type Language, type StoryArchiveItem, type TodayPlan as Plan } from "@/lib/api";
import { cs } from "@/lib/i18n/cs";
import { useHotkeys } from "@/lib/keyboard";

const t = cs.today;
const STEP: Record<Plan["steps"][number]["kind"], { icon: LucideIcon; href: string }> = {
  check: { icon: ClipboardCheck, href: "/check" },
  grammar_check: { icon: GraduationCap, href: "/grammar" },
  lesson: { icon: BookOpen, href: "/lesson" },
  reading: { icon: BookOpenText, href: "/stories" },
};

/** Ring showing today's (estimated) minutes against the profile's own goal. */
function GoalRing({ minutes, goal }: { minutes: number; goal: number }) {
  const r = 34;
  const c = 2 * Math.PI * r;
  const share = Math.min(1, goal ? minutes / goal : 0);
  return (
    <div className="relative size-24 shrink-0" role="img" aria-label={t.ringLabel(minutes, goal)}>
      <svg viewBox="0 0 80 80" className="size-full -rotate-90">
        <circle cx="40" cy="40" r={r} fill="none" strokeWidth="8" className="stroke-slate-100 dark:stroke-slate-800" />
        <circle
          cx="40"
          cy="40"
          r={r}
          fill="none"
          strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={c * (1 - share)}
          className={`${share >= 1 ? "stroke-emerald-500" : "stroke-brand-500"} motion-safe:transition-[stroke-dashoffset] motion-safe:duration-1000`}
        />
      </svg>
      <span className="absolute inset-0 flex flex-col items-center justify-center leading-none">
        <span className="text-xl font-black tabular-nums">{minutes}</span>
        <span className="text-[0.65rem] text-slate-500">/ {goal} min</span>
      </span>
    </div>
  );
}

export function TodayPlan({ language, profileId }: { language: Language; profileId: string }) {
  const router = useRouter();
  const [plan, setPlan] = useState<Plan | null>(null);
  const [recentStories, setRecentStories] = useState<StoryArchiveItem[]>([]);
  useHotkeys(); // Enter on the dashboard continues with the first step
  useEffect(() => {
    let cancelled = false;
    getToday(language)
      .then((p) => !cancelled && setPlan(p))
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [language, profileId]);
  useEffect(() => {
    let cancelled = false;
    listStoryArchive(language)
      .then((items) => !cancelled && setRecentStories(items.slice(0, 3)))
      .catch(() => undefined);
    return () => { cancelled = true; };
  }, [language, profileId]);
  if (!plan) return null;
  const first = plan.steps[0];
  const done = plan.minutes_today >= plan.goal_minutes;
  return (
    <section className="flex flex-col gap-4 rounded-3xl border border-brand-500/30 bg-gradient-to-br from-brand-500/10 via-white to-white p-4 shadow-sm dark:via-slate-900 dark:to-slate-900 sm:flex-row sm:items-center lg:col-span-3">
      <div className="flex items-center gap-4">
        <GoalRing minutes={plan.minutes_today} goal={plan.goal_minutes} />
        <div className="flex flex-col">
          <h2 className="text-lg font-bold">{t.title}</h2>
          <p className="text-sm text-slate-600 dark:text-slate-300">{done ? t.goalMet : t.goal(plan.goal_minutes)}</p>
          <p className="text-xs text-slate-500">{t.estimate(plan.answers_today)}</p>
        </div>
      </div>
      <ol className="flex flex-1 flex-wrap gap-2">
        {plan.steps.length === 0 && <li className="text-sm text-slate-500">{t.nothing}</li>}
        {plan.steps.map((s, i) => {
          const Icon = STEP[s.kind].icon;
          return (
            <li key={s.kind}>
              <button
                type="button"
                onClick={() => router.push(STEP[s.kind].href)}
                className={`flex items-center gap-2 rounded-2xl border px-3 py-2 text-left text-sm hover:border-brand-500 ${
                  i === 0 ? "border-brand-500 bg-white dark:bg-slate-900" : "border-slate-200 bg-white/60 dark:border-slate-800 dark:bg-slate-900/60"
                }`}
              >
                <span className="flex size-6 items-center justify-center rounded-full bg-brand-500/15 text-xs font-bold text-brand-600 dark:text-brand-50">
                  {i + 1}
                </span>
                <Icon className="size-4 text-brand-500" aria-hidden />
                <span className="flex flex-col leading-tight">
                  <span className="font-semibold">{t.step[s.kind]?.(s.count)}</span>
                  <span className="text-xs text-slate-500">~{s.minutes} min</span>
                </span>
              </button>
            </li>
          );
        })}
      </ol>
      {recentStories.length > 0 && (
        <section className="flex min-w-0 flex-col gap-1 sm:max-w-56" aria-label={t.recentReadings}>
          <h3 className="text-xs font-semibold text-slate-500">{t.recentReadings}</h3>
          {recentStories.map((story) => (
            <Link key={story.id} href={`/stories?story=${encodeURIComponent(story.id)}`} className="truncate rounded-lg px-2 py-1 text-sm font-medium text-brand-700 hover:bg-brand-500/10 dark:text-brand-100" title={story.title}>
              {story.title}
            </Link>
          ))}
        </section>
      )}
      {first && (
        <Button className="shrink-0 !py-4" data-hotkey="enter" onClick={() => router.push(STEP[first.kind].href)}>
          {t.go} <ArrowRight className="size-5" aria-hidden /> <KeyHint k="Enter" />
        </Button>
      )}
      {plan.tomorrow_due > 0 && <p className="text-xs text-slate-500 sm:hidden">{t.tomorrow(plan.tomorrow_due)}</p>}
    </section>
  );
}
