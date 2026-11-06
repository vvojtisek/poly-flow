"use client";

import { AlertTriangle, Dumbbell, History, Sparkles } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { AppShell, FullPageStatus, LanguagePicker } from "@/components/AppShell";
import { Notice } from "@/components/ui";
import { getWeakSpots, type Language, type WeakSpots } from "@/lib/api";
import { useAuth, useRequireMe } from "@/lib/auth";
import { cs } from "@/lib/i18n/cs";
import { modesFor, readRecent, SKILLS, type PracticeMode, type Skill } from "@/lib/practice";

const t = cs.practice;
const ERROR_ROUTE: Record<string, (language: Language) => string> = {
  article: (language) => language === "de" ? "/grammar/cases" : "/grammar",
  ending: (language) => ["de", "fr", "it"].includes(language) ? "/grammar/verbs" : "/grammar",
  word_order: () => "/word-order",
  gender: (language) => ["de", "fr", "it"].includes(language) ? "/genders" : "/grammar",
  capitalisation: () => "/dictation",
  diacritics: () => "/dictation",
  spelling: () => "/dictation",
  meaning: () => "/lesson",
  word_choice: () => "/lesson",
};
const TINT = [
  "from-sky-500/15 to-sky-500/0",
  "from-violet-500/15 to-violet-500/0",
  "from-emerald-500/15 to-emerald-500/0",
  "from-amber-500/15 to-amber-500/0",
  "from-rose-500/15 to-rose-500/0",
  "from-brand-500/15 to-brand-500/0",
];

function chip(active: boolean) {
  return `rounded-full px-3 py-1.5 text-sm font-semibold ${
    active ? "bg-brand-500 text-white" : "bg-slate-100 text-slate-700 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
  }`;
}

function Card({ m, tint }: { m: PracticeMode; tint: string }) {
  const copy = t.mode[m.id]!;
  return (
    <Link
      href={m.href}
      className={`group flex h-full flex-col gap-3 rounded-3xl border border-slate-200 bg-gradient-to-br ${tint} p-5 transition-transform hover:-translate-y-0.5 hover:border-brand-500 motion-reduce:transition-none dark:border-slate-800`}
    >
      <span className="flex items-center gap-3">
        <span className="grid size-11 place-items-center rounded-2xl bg-white shadow-sm dark:bg-slate-900">
          <m.icon className="size-6 text-brand-600 dark:text-brand-50" aria-hidden />
        </span>
        <span className="text-lg font-bold">{copy.title}</span>
      </span>
      <span className="text-sm text-slate-600 dark:text-slate-300">{copy.blurb}</span>
      <span className="mt-auto flex flex-wrap gap-1">
        {m.skills.map((s) => (
          <span key={s} className="rounded-full bg-white/70 px-2 py-0.5 text-xs font-medium text-slate-600 dark:bg-slate-900/70 dark:text-slate-300">
            {t.skill[s]}
          </span>
        ))}
      </span>
    </Link>
  );
}

export default function PracticePage() {
  const me = useRequireMe();
  const { state } = useAuth();
  const [skill, setSkill] = useState<Skill | null>(null);
  const [recent, setRecent] = useState<PracticeMode["id"][]>([]);
  const [weakSpots, setWeakSpots] = useState<WeakSpots | null>(null);
  const [weakFailed, setWeakFailed] = useState(false);
  useEffect(() => setRecent(readRecent()), []);
  useEffect(() => {
    if (!me?.acting.active_language) return;
    let cancelled = false;
    setWeakSpots(null);
    setWeakFailed(false);
    getWeakSpots(me.acting.active_language)
      .then((data) => !cancelled && setWeakSpots(data))
      .catch(() => !cancelled && setWeakFailed(true));
    return () => { cancelled = true; };
  }, [me?.acting.active_language, me?.acting.id]);

  if (state.kind === "error") return <FullPageStatus text={cs.common.offline} />;
  if (!me) return <FullPageStatus text={cs.common.loading} />;
  const modes = modesFor(me.acting.active_language);
  const shown = skill ? modes.filter((m) => m.skills.includes(skill)) : modes;
  const last = recent.map((id) => modes.find((m) => m.id === id)).filter((m): m is PracticeMode => !!m);
  const available = SKILLS.filter((s) => modes.some((m) => m.skills.includes(s)));
  const recommendations = (weakSpots?.tags ?? [])
    .filter(([tag]) => !!ERROR_ROUTE[tag])
    .slice(0, 3)
    .map(([tag, count]) => ({ tag, count, href: ERROR_ROUTE[tag]!(me.acting.active_language) }));

  return (
    <AppShell me={me}>
      <section className="flex flex-col gap-4">
        <h1 className="flex items-center gap-2 text-2xl font-bold">
          <Dumbbell className="size-6 text-brand-500" aria-hidden />
          {t.title}
        </h1>
        <p className="max-w-2xl text-slate-600 dark:text-slate-300">{t.intro}</p>
        <LanguagePicker me={me} />

        {(weakFailed || recommendations.length > 0) && (
          <section className="flex flex-col gap-3 rounded-3xl border border-amber-300/70 bg-amber-50/70 p-4 dark:border-amber-900 dark:bg-amber-950/25">
            <div className="flex items-center gap-2">
              <Sparkles className="size-5 text-amber-600 dark:text-amber-300" aria-hidden />
              <h2 className="font-bold">{t.recommendTitle}</h2>
            </div>
            {weakFailed ? (
              <Notice tone="error">{cs.common.error}</Notice>
            ) : (
              <>
                <p className="text-sm text-slate-600 dark:text-slate-300">{t.recommendHelp}</p>
                <ul className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                  {recommendations.map(({ tag, count, href }) => (
                    <li key={tag}>
                      <Link href={href} className="flex h-full items-center justify-between gap-3 rounded-2xl border border-amber-300/60 bg-white p-3 hover:border-amber-500 dark:border-amber-900 dark:bg-slate-900">
                        <span className="flex items-start gap-2">
                          <AlertTriangle className="mt-0.5 size-4 shrink-0 text-amber-600" aria-hidden />
                          <span className="font-semibold">{cs.feedback.errors[tag] ?? tag}</span>
                        </span>
                        <span className="shrink-0 text-xs text-slate-500">{t.recommendCount(count)}</span>
                      </Link>
                    </li>
                  ))}
                </ul>
              </>
            )}
          </section>
        )}

        {last.length > 0 && (
          <div className="flex flex-wrap items-center gap-2">
            <span className="flex items-center gap-1 text-sm font-medium text-slate-500">
              <History className="size-4" aria-hidden /> {t.recent}:
            </span>
            {last.map((m) => (
              <Link
                key={m.id}
                href={m.href}
                className="inline-flex items-center gap-1.5 rounded-full border border-brand-500/40 bg-brand-500/5 px-3 py-1.5 text-sm font-semibold text-brand-600 hover:bg-brand-500/10 dark:text-brand-50"
              >
                <m.icon className="size-4" aria-hidden />
                {t.mode[m.id]?.title}
              </Link>
            ))}
          </div>
        )}

        <div className="flex flex-wrap items-center gap-2" role="radiogroup" aria-label={t.filter}>
          <span className="text-sm font-medium text-slate-500">{t.filter}</span>
          <button type="button" role="radio" aria-checked={skill === null} className={chip(skill === null)} onClick={() => setSkill(null)}>
            {t.all}
          </button>
          {available.map((s) => (
            <button key={s} type="button" role="radio" aria-checked={skill === s} className={chip(skill === s)} onClick={() => setSkill(s)}>
              {t.skill[s]}
            </button>
          ))}
        </div>
        <p className="text-xs text-slate-500" aria-live="polite">
          {t.count(shown.length)}
        </p>

        <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {shown.map((m) => (
            <li key={m.id}>
              <Card m={m} tint={TINT[modes.indexOf(m) % TINT.length]!} />
            </li>
          ))}
        </ul>
      </section>
    </AppShell>
  );
}
