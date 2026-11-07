"use client";

import { AlertTriangle, Dumbbell, History, Pin, PinOff, Sparkles } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { AppShell, FullPageStatus, LanguagePicker } from "@/components/AppShell";
import { Notice } from "@/components/ui";
import { getLanguageSummaries, getWeakSpots, type Language, type WeakSpots } from "@/lib/api";
import { useAuth, useRequireMe } from "@/lib/auth";
import { cs, relativePast } from "@/lib/i18n/cs";
import { modesFor, readPinned, readRecent, readVisits, SKILLS, togglePinned, type PracticeMode, type Skill } from "@/lib/practice";

const t = cs.practice;
const ERROR_ROUTE: Record<string, (language: Language) => string> = {
  article: (language) => language === "de" ? "/grammar/cases" : "/grammar",
  ending: (language) => ["de", "fr", "it"].includes(language) ? "/grammar/verbs" : "/grammar",
  word_order: () => "/word-order",
  gender: (language) => ["de", "fr", "it"].includes(language) ? "/genders" : "/grammar",
  capitalisation: () => "/dictation",
  diacritics: () => "/dictation",
  spelling: () => "/dictation",
  // Missed meanings come back first in the next vocabulary lesson (remediation), so go there.
  meaning: () => "/lesson/vocabulary",
  word_choice: () => "/lesson/vocabulary",
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

function Card({ m, tint, pinned, onToggle, visited, locked }: { m: PracticeMode; tint: string; pinned: boolean; onToggle: () => void; visited: string | undefined; locked: boolean }) {
  const copy = t.mode[m.id]!;
  return (
    <div className={`relative h-full rounded-3xl border border-slate-200 bg-gradient-to-br ${tint} transition-transform hover:-translate-y-0.5 hover:border-brand-500 motion-reduce:transition-none dark:border-slate-800`}>
      <Link href={m.href} className="group flex h-full flex-col gap-3 p-5 pr-14">
        <span className="flex items-center gap-3">
          <span className="grid size-11 place-items-center rounded-2xl bg-white shadow-sm dark:bg-slate-900">
            <m.icon className="size-6 text-brand-600 dark:text-brand-50" aria-hidden />
          </span>
          <span className="text-lg font-bold">{copy.title}</span>
        </span>
        <span className="text-sm text-slate-600 dark:text-slate-300">{copy.blurb}</span>
        {locked ? (
          <span className="text-xs font-semibold text-amber-700 dark:text-amber-300">{t.needsLesson}</span>
        ) : (
          <span className="text-xs text-slate-500">{visited ? t.lastVisit(relativePast(visited)) : t.neverVisited}</span>
        )}
        <span className="mt-auto flex flex-wrap gap-1">
          {m.skills.map((s) => (
            <span key={s} className="rounded-full bg-white/70 px-2 py-0.5 text-xs font-medium text-slate-600 dark:bg-slate-900/70 dark:text-slate-300">
              {t.skill[s]}
            </span>
          ))}
        </span>
      </Link>
      <button type="button" aria-pressed={pinned} aria-label={pinned ? t.unpinMode(copy.title) : t.pinMode(copy.title)} title={pinned ? t.unpinMode(copy.title) : t.pinMode(copy.title)} onClick={onToggle} className="absolute right-3 top-3 rounded-full bg-white/80 p-2 text-brand-700 hover:bg-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 dark:bg-slate-900/80 dark:text-brand-100 dark:hover:bg-slate-900">
        {pinned ? <PinOff className="size-4" aria-hidden /> : <Pin className="size-4" aria-hidden />}
      </button>
    </div>
  );
}

export default function PracticePage() {
  const me = useRequireMe();
  const { state } = useAuth();
  const [skills, setSkills] = useState<Skill[]>([]);
  const [recent, setRecent] = useState<PracticeMode["id"][]>([]);
  const [pinned, setPinned] = useState<PracticeMode["id"][]>([]);
  const [weakSpots, setWeakSpots] = useState<WeakSpots | null>(null);
  const [weakFailed, setWeakFailed] = useState(false);
  // Words met in this language; modes built on them are marked until the first lesson.
  const [introduced, setIntroduced] = useState<number | null>(null);
  useEffect(() => setRecent(readRecent()), []);
  useEffect(() => setPinned(readPinned()), []);
  const [visits, setVisits] = useState<ReturnType<typeof readVisits>>({});
  useEffect(() => setVisits(readVisits()), []);
  useEffect(() => {
    if (!me?.acting.active_language) return;
    let cancelled = false;
    setWeakSpots(null);
    setWeakFailed(false);
    setIntroduced(null);
    getLanguageSummaries()
      .then((rows) => !cancelled && setIntroduced(rows.find((r) => r.language === me.acting.active_language)?.introduced ?? 0))
      .catch(() => undefined);
    getWeakSpots(me.acting.active_language)
      .then((data) => !cancelled && setWeakSpots(data))
      .catch(() => !cancelled && setWeakFailed(true));
    return () => { cancelled = true; };
  }, [me?.acting.active_language, me?.acting.id]);

  if (state.kind === "error") return <FullPageStatus text={cs.common.offline} />;
  if (!me) return <FullPageStatus text={cs.common.loading} />;
  const modes = modesFor(me.acting.active_language);
  const shown = skills.length ? modes.filter((m) => m.skills.some((skill) => skills.includes(skill))) : modes;
  const last = recent.map((id) => modes.find((m) => m.id === id)).filter((m): m is PracticeMode => !!m);
  const favorites = pinned.map((id) => modes.find((m) => m.id === id)).filter((m): m is PracticeMode => !!m);
  const available = SKILLS.filter((s) => modes.some((m) => m.skills.includes(s)));
  const recommendations = (weakSpots?.tags ?? [])
    .filter(([tag]) => !!ERROR_ROUTE[tag])
    .slice(0, 3)
    .map(([tag, count]) => ({
      tag,
      count,
      href: ERROR_ROUTE[tag]!(me.acting.active_language),
      // The words and topics behind this kind of mistake, so the advice is concrete.
      examples: [
        ...(weakSpots?.words ?? []).filter((w) => w.tags.includes(tag)).map((w) => (me.acting.active_language === "de" && w.gender ? `${w.gender} ${w.lemma}` : w.lemma)),
        ...(weakSpots?.units ?? []).filter((u) => u.tags.includes(tag)).map((u) => u.title),
      ].slice(0, 3),
    }));

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
                  {recommendations.map(({ tag, count, href, examples }) => (
                    <li key={tag}>
                      <Link href={href} className="flex h-full flex-col gap-1 rounded-2xl border border-amber-300/60 bg-white p-3 hover:border-amber-500 dark:border-amber-900 dark:bg-slate-900">
                        <span className="flex items-start justify-between gap-3">
                          <span className="flex items-start gap-2">
                            <AlertTriangle className="mt-0.5 size-4 shrink-0 text-amber-600" aria-hidden />
                            <span className="font-semibold">{cs.feedback.errors[tag] ?? tag}</span>
                          </span>
                          <span className="shrink-0 text-xs text-slate-500">{t.recommendCount(count)}</span>
                        </span>
                        {examples.length > 0 && (
                          <span className="pl-6 text-xs text-slate-600 dark:text-slate-300">
                            {t.recommendExamples}{" "}
                            <span lang={me.acting.active_language}>{examples.join(", ")}</span>
                          </span>
                        )}
                        <span className="pl-6 text-xs font-semibold text-amber-700 dark:text-amber-300">{t.recommendGo[tag] ?? t.recommendGoDefault}</span>
                      </Link>
                    </li>
                  ))}
                </ul>
              </>
            )}
          </section>
        )}

        {favorites.length > 0 && (
          <section className="flex flex-wrap items-center gap-2" aria-label={t.pinned}>
            <span className="flex items-center gap-1 text-sm font-medium text-slate-500"><Pin className="size-4" aria-hidden /> {t.pinned}:</span>
            {favorites.map((m) => <Link key={m.id} href={m.href} className="inline-flex items-center gap-1.5 rounded-full border border-brand-500 bg-brand-500/10 px-3 py-1.5 text-sm font-semibold text-brand-700 dark:text-brand-50"><m.icon className="size-4" aria-hidden />{t.mode[m.id]?.title}</Link>)}
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

        <div className="flex flex-wrap items-center gap-2" role="group" aria-label={t.filter}>
          <span className="text-sm font-medium text-slate-500">{t.filter}</span>
          <button type="button" aria-pressed={skills.length === 0} className={chip(skills.length === 0)} onClick={() => setSkills([])}>
            {t.all}
          </button>
          {available.map((s) => (
            <button key={s} type="button" aria-pressed={skills.includes(s)} className={chip(skills.includes(s))} onClick={() => setSkills((current) => current.includes(s) ? current.filter((item) => item !== s) : [...current, s])}>
              {t.skill[s]}
            </button>
          ))}
        </div>
        {skills.length > 0 && <p className="-mt-2 text-xs text-slate-500">{t.filterHelp}</p>}
        <p className="text-xs text-slate-500" aria-live="polite">
          {t.count(shown.length)}
        </p>

        <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {shown.map((m) => (
            <li key={m.id}>
              <Card m={m} tint={TINT[modes.indexOf(m) % TINT.length]!} pinned={pinned.includes(m.id)} onToggle={() => setPinned(togglePinned(m.id))} visited={visits[m.id]} locked={!!m.needsWords && introduced === 0} />
            </li>
          ))}
        </ul>
      </section>
    </AppShell>
  );
}
