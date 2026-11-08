"use client";

import { AlertTriangle, ArrowRight, Dumbbell, Layers, Lightbulb, Pin, PinOff, Sparkles } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { AppShell, FullPageStatus, LanguagePicker } from "@/components/AppShell";
import { FlashcardSession } from "@/components/FlashcardSession";
import { RetryNotice } from "@/components/ui";
import { getLanguageSummaries, getWeakSpots, type Language, type WeakSpots } from "@/lib/api";
import { useAuth, useRequireMe } from "@/lib/auth";
import { KeyHint } from "@/components/Kbd";
import { cs, relativePast } from "@/lib/i18n/cs";
import { useHotkeys } from "@/lib/keyboard";
import { modesFor, readPinned, readVisits, SKILLS, suggestModes, togglePinned, type PracticeMode, type Skill } from "@/lib/practice";

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

function Card({ m, tint, pinned, onToggle, visited, locked, hotkey }: { m: PracticeMode; tint: string; pinned: boolean; onToggle: () => void; visited: string | undefined; locked: boolean; hotkey?: number }) {
  const copy = t.mode[m.id]!;
  return (
    <div className={`relative h-full rounded-3xl border border-slate-200 bg-gradient-to-br ${tint} transition-transform hover:-translate-y-0.5 hover:border-brand-500 motion-reduce:transition-none dark:border-slate-800`}>
      <Link
        href={m.href}
        data-hotkey={hotkey ? String(hotkey) : undefined}
        aria-keyshortcuts={hotkey ? String(hotkey) : undefined}
        className="group flex h-full flex-col gap-2 p-4 pr-14 sm:gap-3 sm:p-5 sm:pr-14"
      >
        <span className="flex items-center gap-3">
          <span className="grid size-9 shrink-0 place-items-center rounded-xl bg-white shadow-sm sm:size-11 sm:rounded-2xl dark:bg-slate-900">
            <m.icon className="size-5 text-brand-600 sm:size-6 dark:text-brand-50" aria-hidden />
          </span>
          <span className="text-lg font-bold">{copy.title}</span>
          {hotkey && <KeyHint k={String(hotkey)} />}
        </span>
        <span className="line-clamp-2 text-sm text-slate-600 sm:line-clamp-none dark:text-slate-300">{copy.blurb}</span>
        {locked ? (
          <span className="text-xs font-semibold text-amber-700 dark:text-amber-300">{t.needsLesson}</span>
        ) : (
          <span className="text-xs text-slate-500">{visited ? t.lastVisit(relativePast(visited)) : t.neverVisited}</span>
        )}
        {/* Skills are also the filter chips; on phones the card stays short without them. */}
        <span className="mt-auto hidden flex-wrap gap-1 sm:flex">
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
  useHotkeys(); // 1-9 open the visible cards in order, Enter opens today's tip
  const [pinned, setPinned] = useState<PracticeMode["id"][]>([]);
  const [weakSpots, setWeakSpots] = useState<WeakSpots | null>(null);
  const [weakFailed, setWeakFailed] = useState(false);
  const [weakCards, setWeakCards] = useState(false);
  const [tipIndex, setTipIndex] = useState(0);
  const [announce, setAnnounce] = useState("");
  // Words met in this language; modes built on them are marked until the first lesson.
  const [introduced, setIntroduced] = useState<number | null>(null);
  // The summary is optional: if it fails, treat the count as unknown and lock nothing.
  const [summaryDone, setSummaryDone] = useState(false);
  const [attempt, setAttempt] = useState(0);
  // The skill filter lives in the URL (?skill=listening,speaking), so it survives back navigation
  // from a practice mode and can be linked to.
  const [urlRead, setUrlRead] = useState(false);
  useEffect(() => {
    const raw = new URLSearchParams(window.location.search).get("skill") ?? "";
    setSkills(raw.split(",").filter((x): x is Skill => (SKILLS as string[]).includes(x)));
    setUrlRead(true);
  }, []);
  useEffect(() => {
    if (!urlRead) return;
    const params = new URLSearchParams(window.location.search);
    if (skills.length) params.set("skill", skills.join(","));
    else params.delete("skill");
    const qs = params.toString();
    window.history.replaceState(window.history.state, "", `${window.location.pathname}${qs ? `?${qs}` : ""}`);
  }, [urlRead, skills]);
  const profileId = me?.acting.id;
  useEffect(() => setPinned(profileId ? readPinned(profileId) : []), [profileId]);
  const [visits, setVisits] = useState<ReturnType<typeof readVisits>>({});
  useEffect(() => setVisits(profileId ? readVisits(profileId) : {}), [profileId]);
  useEffect(() => {
    if (!me?.acting.active_language) return;
    let cancelled = false;
    setWeakSpots(null);
    setWeakFailed(false);
    setIntroduced(null);
    setSummaryDone(false);
    getLanguageSummaries()
      .then((rows) => !cancelled && setIntroduced(rows.find((r) => r.language === me.acting.active_language)?.introduced ?? 0))
      .catch(() => undefined)
      .finally(() => !cancelled && setSummaryDone(true));
    getWeakSpots(me.acting.active_language)
      .then((data) => !cancelled && setWeakSpots(data))
      .catch(() => !cancelled && setWeakFailed(true));
    return () => { cancelled = true; };
  }, [me?.acting.active_language, me?.acting.id, attempt]);

  if (state.kind === "error") return <FullPageStatus text={cs.common.offline} />;
  if (!me) return <FullPageStatus text={cs.common.loading} />;
  const modes = modesFor(me.acting.active_language);
  // Pinned modes lead the grid (in pin order), so their 1-9 shortcuts stay put.
  const filtered = skills.length ? modes.filter((m) => m.skills.some((skill) => skills.includes(skill))) : modes;
  const pinRank = (m: PracticeMode) => (pinned.includes(m.id) ? pinned.indexOf(m.id) : pinned.length + modes.indexOf(m));
  const shown = [...filtered].sort((a, b) => pinRank(a) - pinRank(b));
  // Wait for the word count before suggesting, so the tip does not jump to another mode.
  const tips = !summaryDone ? [] : suggestModes(modes, visits, (m) => !(m.needsWords && introduced === 0));
  const tip = tips.length ? tips[tipIndex % tips.length]! : null;
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

  if (weakCards)
    return (
      <AppShell me={me}>
        <FlashcardSession language={me.acting.active_language} scope={{ kind: "weak", label: t.weakDeck }} onClose={() => setWeakCards(false)} closeLabel={t.backToHub} />
      </AppShell>
    );

  return (
    <AppShell me={me}>
      <section className="flex flex-col gap-4">
        <h1 className="flex items-center gap-2 text-2xl font-bold">
          <Dumbbell className="size-6 text-brand-500" aria-hidden />
          {t.title}
        </h1>
        <p className="max-w-2xl text-slate-600 dark:text-slate-300">{t.intro}</p>
        <LanguagePicker me={me} />

        {!summaryDone && <div aria-hidden className="h-[88px] rounded-3xl border border-brand-500/20 bg-brand-500/5 motion-safe:animate-pulse" />}
        {tip && (
          <div className="flex items-stretch gap-2 rounded-3xl border border-brand-500/40 bg-brand-500/5 p-2 sm:p-3">
            <Link
              href={tip.mode.href}
              data-hotkey="enter"
              aria-keyshortcuts="Enter"
              className="flex min-w-0 flex-1 items-center gap-3 rounded-2xl p-2 hover:bg-brand-500/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
            >
              <span className="grid size-11 shrink-0 place-items-center rounded-2xl bg-white shadow-sm dark:bg-slate-900">
                <Lightbulb className="size-6 text-brand-600 dark:text-brand-50" aria-hidden />
              </span>
              <span className="flex min-w-0 flex-1 flex-col" aria-live="polite">
                <span className="text-xs font-semibold uppercase tracking-wide text-brand-700 dark:text-brand-200">{t.tipTitle}</span>
                <span className="font-bold">{t.mode[tip.mode.id]?.title}</span>
                <span className="text-sm text-slate-600 dark:text-slate-300">
                  {tip.since ? t.tipSince(t.skill[tip.skill] ?? tip.skill, relativePast(tip.since)) : t.tipNever(t.skill[tip.skill] ?? tip.skill)}
                </span>
              </span>
              <KeyHint k="Enter" />
              <ArrowRight className="size-5 shrink-0 text-brand-600" aria-hidden />
            </Link>
            {tips.length > 1 && (
              <button
                type="button"
                onClick={() => setTipIndex((i) => i + 1)}
                className="shrink-0 self-center rounded-xl px-3 py-2 text-sm font-semibold text-brand-700 hover:bg-brand-500/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 dark:text-brand-100"
              >
                {t.tipOther}
              </button>
            )}
          </div>
        )}

        {(weakFailed || recommendations.length > 0) && (
          <section className="flex flex-col gap-3 rounded-3xl border border-amber-300/70 bg-amber-50/70 p-4 dark:border-amber-900 dark:bg-amber-950/25">
            <div className="flex items-center gap-2">
              <Sparkles className="size-5 text-amber-600 dark:text-amber-300" aria-hidden />
              <h2 className="font-bold">{t.recommendTitle}</h2>
            </div>
            {weakFailed ? (
              <RetryNotice text={t.weakFailed} onRetry={() => setAttempt((n) => n + 1)} />
            ) : (
              <>
                <p className="text-sm text-slate-600 dark:text-slate-300">{t.recommendHelp}</p>
                {(weakSpots?.words.length ?? 0) > 0 && (
                  <button
                    type="button"
                    onClick={() => setWeakCards(true)}
                    className="inline-flex items-center gap-2 self-start rounded-xl bg-amber-500 px-3 py-2 text-sm font-semibold text-white hover:bg-amber-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-500 focus-visible:ring-offset-2"
                  >
                    <Layers className="size-4" aria-hidden /> {t.weakCards(weakSpots!.words.length)}
                  </button>
                )}
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

        <span id="skill-filter" className="-mb-2 text-sm font-medium text-slate-500">{t.filter}</span>
        {/* Phones: one swipeable chip row; wider screens wrap. */}
        <div
          className="-mx-4 flex gap-2 overflow-x-auto px-4 pb-1 [scrollbar-width:none] sm:mx-0 sm:flex-wrap sm:overflow-visible sm:px-0 sm:pb-0 [&>button]:shrink-0 [&>button]:whitespace-nowrap"
          role="group"
          aria-labelledby="skill-filter"
        >
          <button type="button" aria-pressed={skills.length === 0} className={chip(skills.length === 0)} onClick={() => setSkills([])}>
            {t.all}
          </button>
          {available.map((s) => (
            <button key={s} type="button" aria-pressed={skills.includes(s)} className={chip(skills.includes(s))} onClick={() => setSkills((current) => current.includes(s) ? current.filter((item) => item !== s) : [...current, s])}>
              {t.skill[s]} <span className="tabular-nums opacity-70">{modes.filter((m) => m.skills.includes(s)).length}</span>
            </button>
          ))}
        </div>
        {skills.length > 0 && <p className="-mt-2 text-xs text-slate-500">{t.filterHelp}</p>}
        <p className="text-xs text-slate-500" aria-live="polite">
          {t.count(shown.length)}
        </p>
        <p className="sr-only" aria-live="polite">
          {announce}
        </p>

        <ul className="grid gap-2 sm:grid-cols-2 sm:gap-3 lg:grid-cols-3">
          {shown.map((m, i) => (
            <li key={m.id}>
              <Card m={m} tint={TINT[modes.indexOf(m) % TINT.length]!} pinned={pinned.includes(m.id)} onToggle={() => {
                  const next = togglePinned(me.acting.id, m.id);
                  setPinned(next);
                  setAnnounce(next.includes(m.id) ? t.pinnedNow(t.mode[m.id]?.title ?? m.id) : t.unpinnedNow(t.mode[m.id]?.title ?? m.id));
                }} visited={visits[m.id]} locked={!!m.needsWords && introduced === 0} hotkey={i < 9 ? i + 1 : undefined} />
            </li>
          ))}
        </ul>
      </section>
    </AppShell>
  );
}
