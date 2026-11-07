"use client";

import { BookOpen, CheckCircle2, ChevronRight, Compass, Gauge, GraduationCap, LifeBuoy, PlayCircle, RefreshCw } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { AppShell, FullPageStatus, LanguagePicker } from "@/components/AppShell";
import { Notice, RetryNotice, Skeleton } from "@/components/ui";
import { PlayButton } from "@/components/PlayButton";
import { getDiagnosticInfo, getGrammarTree, getGrammarUnit, getLessonPreview, grammarExampleAudioUrl, getProgress, type CefrLevel, type GrammarTree, type GrammarUnitSummary, type LessonPreview, type LevelBadge } from "@/lib/api";
import { useRequireMe } from "@/lib/auth";
import { isTypingTarget, useHotkeys } from "@/lib/keyboard";
import { KeyHint } from "@/components/Kbd";
import { cs } from "@/lib/i18n/cs";

const PRIMARY = "mt-4 inline-flex min-h-11 items-center justify-center gap-2 rounded-xl bg-brand-500 px-4 py-2 font-semibold text-white hover:bg-brand-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2";
type Show = "all" | "new" | "studied" | "due";
const SHOWS: Show[] = ["all", "new", "studied", "due"];
const SHOW_TEST: Record<Exclude<Show, "all">, (u: GrammarUnitSummary) => boolean> = {
  new: (u) => u.status === "new",
  studied: (u) => u.status !== "new",
  due: (u) => u.due,
};
const REVISIT = 3;
const LEVELS: CefrLevel[] = ["A1", "A2", "B1", "B2", "C1", "C2"];
const NEXT: Record<string, CefrLevel> = { "pre-A1": "A1", A1: "A2", A2: "B1", B1: "B2", B2: "C1", "B2+": "C1", C1: "C2", C2: "C2" };

/** The topic's first example, heard and read before starting: context before the lesson itself. */
function ExampleTaste({ unitId, language }: { unitId: string; language: string }) {
  const [example, setExample] = useState<{ text: string; cs: string } | null>(null);
  useEffect(() => {
    let live = true;
    setExample(null);
    getGrammarUnit(unitId)
      .then((u) => live && setExample(u.examples[0] ?? null))
      .catch(() => undefined); // optional: the card works without it
    return () => {
      live = false;
    };
  }, [unitId]);
  if (!example) return null;
  return (
    <div className="mt-3 flex items-center gap-2 rounded-xl bg-white/70 px-3 py-2 dark:bg-slate-900/60">
      <PlayButton url={grammarExampleAudioUrl(unitId, 0)} size="sm" label={cs.audio.playSentence} hotkey />
      <div className="min-w-0">
        <p className="text-sm italic" lang={language}>
          {example.text}
        </p>
        <p className="text-xs text-slate-500">{example.cs}</p>
      </div>
      <KeyHint k="P" />
    </div>
  );
}

type Estimate = { level: string; at: string | null; source: "test" | "progress" };
type Snapshot = {
  tree: GrammarTree;
  partial: boolean;
  placement: string | null;
  estimate: Estimate | null;
  testOpen: boolean;
  testAvailable: boolean;
  badge: string | null;
  introduced: number | null;
  openSession: boolean;
  preview: LessonPreview | null;
};
/** Last complete overview per profile and language, for this browser tab only (module memory). */
const SNAPSHOTS = new Map<string, Snapshot>();

function highestBadge(badges: LevelBadge[]): string | null {
  const rank = ["A1", "A2", "B1", "B2"];
  return badges.map((b) => b.level).sort((a, b) => rank.indexOf(b) - rank.indexOf(a))[0] ?? null;
}

export default function LessonPage() {
  const me = useRequireMe();
  useHotkeys(); // Enter opens the recommended step, P plays its example
  const router = useRouter();
  // V opens the vocabulary lesson (letters are free on this page: no text input).
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.defaultPrevented || e.ctrlKey || e.metaKey || e.altKey || isTypingTarget(e.target)) return;
      if (e.code === "KeyV") {
        e.preventDefault();
        router.push("/lesson/vocabulary");
      }
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [router]);
  const language = me?.acting.active_language;
  const profileId = me?.acting.id;
  const [tree, setTree] = useState<GrammarTree | null>(null);
  const [placement, setPlacement] = useState<string | null>(null);
  const [badge, setBadge] = useState<string | null>(null);
  const [introduced, setIntroduced] = useState<number | null>(null);
  const [failed, setFailed] = useState(false);
  // The estimate and vocabulary progress are optional refinements; when they fail, say so instead
  // of presenting "no estimate yet", which would turn missing data into a claim.
  const [partial, setPartial] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const [openSession, setOpenSession] = useState(false);
  const [estimate, setEstimate] = useState<Estimate | null>(null);
  const [testOpen, setTestOpen] = useState(false);
  const [testAvailable, setTestAvailable] = useState(false);
  const [show, setShowState] = useState<Show>("all");
  // The filter lives in the URL so Back from a topic returns to the same list.
  useEffect(() => {
    const wanted = new URLSearchParams(window.location.search).get("show");
    if (wanted && (SHOWS as string[]).includes(wanted)) setShowState(wanted as Show);
  }, []);
  function setShow(value: Show) {
    setShowState(value);
    const params = new URLSearchParams(window.location.search);
    if (value === "all") params.delete("show");
    else params.set("show", value);
    const qs = params.toString();
    window.history.replaceState(window.history.state, "", `${window.location.pathname}${qs ? `?${qs}` : ""}`);
  }
  const [preview, setPreview] = useState<LessonPreview | null>(null);

  useEffect(() => {
    if (!language || !profileId) return;
    let live = true;
    const key = `${profileId}:${language}`;
    function apply(snap: Snapshot) {
      setTree(snap.tree);
      setPartial(snap.partial);
      setPlacement(snap.placement);
      setEstimate(snap.estimate);
      setTestOpen(snap.testOpen);
      setTestAvailable(snap.testAvailable);
      setBadge(snap.badge);
      setIntroduced(snap.introduced);
      setOpenSession(snap.openSession);
      setPreview(snap.preview);
    }
    // Coming back from a topic shows the last overview at once and refreshes it underneath, instead
    // of a skeleton flash on every Back. A different profile or language never shares an entry.
    const cached = SNAPSHOTS.get(key);
    setFailed(false);
    if (cached) apply(cached);
    else {
      setTree(null);
      setPreview(null);
      setOpenSession(false);
      setPartial(false);
    }
    // The grammar tree is the page; the estimate, progress and lesson preview only refine it, so
    // one of them failing must not blank the whole overview.
    Promise.allSettled([getGrammarTree(language), getDiagnosticInfo(language), getProgress(language), getLessonPreview(language)]).then(
      ([grammar, assessment, progress, next]) => {
        if (!live) return;
        if (grammar.status === "rejected") {
          // A cached overview may be stale; do not keep presenting it as current.
          SNAPSHOTS.delete(key);
          setTree(null);
          setFailed(true);
          return;
        }
        const p = progress.status === "fulfilled" ? progress.value : null;
        const a = assessment.status === "fulfilled" ? assessment.value : null;
        const snap: Snapshot = {
          tree: grammar.value,
          partial: assessment.status === "rejected" || progress.status === "rejected",
          placement: a?.latest?.level ?? p?.cefr_level ?? null,
          estimate: a?.latest
            ? { level: a.latest.level, at: a.latest.decided_at, source: "test" }
            : p?.cefr_level
              ? { level: p.cefr_level, at: null, source: "progress" }
              : null,
          testOpen: Boolean(a?.active_session_id),
          testAvailable: Boolean(a?.available),
          badge: p ? highestBadge(p.level_badges) : null,
          introduced: p?.introduced ?? null,
          openSession: Boolean(p?.active_session_id),
          preview: next.status === "fulfilled" ? next.value : null,
        };
        if (!snap.partial) SNAPSHOTS.set(key, snap);
        apply(snap);
      },
    );
    return () => {
      live = false;
    };
  }, [language, profileId, attempt]);

  // What to do next, in order: finish a lesson that is open, clear due checks, then the first topic
  // not studied yet, starting at the level after the learner's estimate. A studied topic is never
  // recommended again as "new"; when everything is studied, only due checks are suggested.
  const next = useMemo(() => {
    if (!tree) return null;
    const all = tree.levels.flatMap((section) => section.units);
    const open = tree.active_lesson_unit ? all.find((u) => u.id === tree.active_lesson_unit) : undefined;
    if (open) return { kind: "resume" as const, unit: open };
    const available = tree.levels.filter((section) => section.units.length > 0);
    if (!available.length) return null;
    const current = placement ?? badge ?? "pre-A1";
    const target = NEXT[current] ?? "A1";
    const rank = (level: CefrLevel) => LEVELS.indexOf(level);
    const fresh = (level: CefrLevel) => available.find((section) => section.level === level)?.units.find((u) => u.status === "new");
    // Target level first, then higher levels, then gaps in lower levels.
    const order = [...available].sort((a, b) => {
      const da = rank(a.level) - rank(target), db = rank(b.level) - rank(target);
      return (da < 0 ? 100 - da : da) - (db < 0 ? 100 - db : db);
    });
    const chosen = order.find((section) => fresh(section.level));
    const source = placement ? "placement" : badge ? "vocabulary" : "new";
    if (chosen) {
      return { kind: "new" as const, level: chosen.level, unit: fresh(chosen.level)!, target, current, source, fallback: chosen.level !== target };
    }
    if (tree.due > 0) return { kind: "check" as const, due: tree.due };
    return { kind: "done" as const };
  }, [tree, placement, badge]);

  if (!me) return <FullPageStatus text={cs.common.loading} />;
  const focusLevel = next?.kind === "new" ? next.level : next?.kind === "resume" ? next.unit.level : (NEXT[placement ?? badge ?? "pre-A1"] ?? "A1");
  const allUnits = tree?.levels.flatMap((section) => section.units) ?? [];
  const emptyLevels = LEVELS.filter((level) => !tree?.levels.find((section) => section.level === level)?.units.length);
  // Scaffolding after a failed check: topics with recent check mistakes, worst first, pointing back
  // to the ungraded lesson (explanation, examples, and the missed exercises as remediation).
  const skip = next && next.kind !== "check" && next.kind !== "done" ? next.unit.id : null;
  const revisit = allUnits
    .filter((u) => u.recent_errors > 0 && u.id !== skip)
    .sort((a, b) => b.recent_errors - a.recent_errors || LEVELS.indexOf(a.level) - LEVELS.indexOf(b.level))
    .slice(0, REVISIT);
  return (
    <AppShell me={me}>
      <div className="mx-auto flex w-full max-w-4xl flex-col gap-5">
        <header className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h1 className="flex items-center gap-2 text-2xl font-bold"><BookOpen className="size-6 text-brand-500" aria-hidden />{cs.lesson.discoveryTitle}</h1>
            <p className="mt-1 max-w-2xl text-sm text-slate-600 dark:text-slate-300">{cs.lesson.discoveryIntro}</p>
          </div>
          <LanguagePicker me={me} />
        </header>

        {tree && (
          // Where the recommendation comes from, and how to change it.
          <p className="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-slate-600 dark:text-slate-300">
            <Gauge className="size-4 text-slate-400" aria-hidden />
            {partial && !estimate && !badge
              ? cs.lesson.estimateFailed
              : estimate
              ? estimate.source === "test" && estimate.at
                ? cs.lesson.estimateFromTest(estimate.level, new Date(estimate.at).toLocaleDateString("cs-CZ"))
                : cs.lesson.estimateFromProgress(estimate.level)
              : badge
                ? cs.lesson.estimateFromBadge(badge)
                : cs.lesson.noEstimate}
            {testAvailable && (
              <Link href="/placement/cefr" className="font-medium text-brand-700 hover:underline dark:text-brand-200">
                {testOpen ? cs.lesson.resumeTest : estimate?.source === "test" ? cs.lesson.retakeTest : cs.lesson.takeTest}
              </Link>
            )}
          </p>
        )}
        {failed && <RetryNotice text={cs.lesson.treeFailed} onRetry={() => setAttempt((n) => n + 1)} />}
        {partial && tree && (
          <button type="button" onClick={() => setAttempt((n) => n + 1)} className="self-start text-xs font-semibold text-brand-700 hover:underline dark:text-brand-200">
            {cs.lesson.partialRetry}
          </button>
        )}
        {!tree && !failed && (
          <div className="flex flex-col gap-5" aria-busy>
            <div className="rounded-2xl border border-slate-200 p-4 dark:border-slate-800 sm:p-5"><Skeleton lines={4} /></div>
            <div className="rounded-2xl border border-slate-200 p-4 dark:border-slate-800"><Skeleton lines={2} /></div>
          </div>
        )}

        {next?.kind === "resume" && (
          <section className="rounded-2xl border border-brand-500/40 bg-brand-500/5 p-4 sm:p-5">
            <p className="mb-1 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-brand-700 dark:text-brand-200"><PlayCircle className="size-4" aria-hidden />{cs.lesson.openLessonLabel}</p>
            <h2 className="text-xl font-bold">{next.unit.title}</h2>
            <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">{next.unit.summary}</p>
            {language && <ExampleTaste unitId={next.unit.id} language={language} />}
            <Link href={`/grammar/${next.unit.id}`} className={PRIMARY} data-hotkey="enter">
              <GraduationCap className="size-5" aria-hidden />{cs.lesson.resume}
              <KeyHint k="Enter" />
            </Link>
          </section>
        )}
        {next?.kind === "new" && (
          <section className="rounded-2xl border border-brand-500/40 bg-brand-500/5 p-4 sm:p-5">
            <p className="mb-1 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-brand-700 dark:text-brand-200"><Compass className="size-4" aria-hidden />{cs.lesson.recommendedFor(next.level)}</p>
            <h2 className="text-xl font-bold">{next.unit.title}</h2>
            <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">{next.unit.summary}</p>
            {language && <ExampleTaste unitId={next.unit.id} language={language} />}
            <p className="mt-2 text-xs text-slate-500">{next.fallback
              ? cs.lesson.recommendFallback(next.target, next.level)
              : next.source === "placement"
                ? cs.lesson.recommendReason(next.current, next.target)
                : next.source === "vocabulary"
                  ? cs.lesson.recommendVocabulary(next.current, next.target)
                  : cs.lesson.recommendNewUser(next.target)}</p>
            <div className="mt-4 flex flex-wrap items-center gap-2">
              <Link href={`/grammar/${next.unit.id}`} className={PRIMARY.replace("mt-4 ", "")} data-hotkey="enter">
                <GraduationCap className="size-5" aria-hidden />{cs.lesson.startRecommended}
                <KeyHint k="Enter" />
              </Link>
              {tree && tree.due > 0 && (
                <Link href="/grammar/check" className="inline-flex min-h-11 items-center gap-2 rounded-xl px-4 py-2 text-sm font-semibold hover:bg-slate-100 dark:hover:bg-slate-800">
                  <RefreshCw className="size-4" aria-hidden />{cs.lesson.checkDue(tree.due)}
                </Link>
              )}
            </div>
          </section>
        )}
        {next?.kind === "check" && (
          <section className="rounded-2xl border border-amber-400/50 bg-amber-50 p-4 dark:bg-amber-950/30 sm:p-5">
            <h2 className="text-lg font-bold">{cs.lesson.allStudiedTitle}</h2>
            <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">{cs.lesson.allStudiedDue(next.due)}</p>
            <Link href="/grammar/check" className={PRIMARY} data-hotkey="enter">
              <RefreshCw className="size-5" aria-hidden />{cs.lesson.checkDue(next.due)}
              <KeyHint k="Enter" />
            </Link>
          </section>
        )}
        {next?.kind === "done" && <Notice>{cs.lesson.allStudied}</Notice>}

        {revisit.length > 0 && (
          <section aria-labelledby="revisit-title" className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
            <h2 id="revisit-title" className="flex items-center gap-2 text-lg font-bold"><LifeBuoy className="size-5 text-amber-500" aria-hidden />{cs.lesson.revisitTitle}</h2>
            <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">{cs.lesson.revisitHelp}</p>
            <ul className="mt-3 flex flex-col gap-2">
              {revisit.map((unit) => (
                <li key={unit.id}>
                  <Link href={`/grammar/${unit.id}`} className="flex min-h-11 items-center justify-between gap-3 rounded-xl border border-slate-200 px-3 py-2 hover:border-brand-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 dark:border-slate-700">
                    <span className="min-w-0">
                      <span className="block truncate font-semibold">{unit.title}</span>
                      <span className="block text-xs text-slate-500">{unit.level} · {cs.lesson.revisitErrors(unit.recent_errors)}</span>
                    </span>
                    <span className="shrink-0 text-sm font-semibold text-brand-700 dark:text-brand-200">{cs.lesson.revisitOpen}</span>
                  </Link>
                </li>
              ))}
            </ul>
          </section>
        )}

        <section className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
          <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
            <h2 className="text-lg font-bold">{cs.lesson.vocabularyCourse}</h2>
            <span className="text-xs text-slate-500">{introduced !== null ? cs.lesson.vocabularyProgress(introduced) : !tree && !failed ? cs.common.loading : null}</span>
          </div>
          <p className="mb-3 text-sm text-slate-600 dark:text-slate-300">{cs.lesson.vocabularyCourseHelp}</p>
          {!openSession && preview && (
            <p className="mb-3 rounded-xl bg-slate-50 px-3 py-2 text-sm dark:bg-slate-800/60">
              {preview.new_words === 0 && preview.review_words === 0 ? (
                cs.lesson.empty
              ) : (
                <>
                  <span className="font-semibold">{preview.scene_title ? cs.dashboard.nextScene(preview.scene_title) : cs.dashboard.nextWords}</span>
                  <span className="block text-xs text-slate-500">{cs.dashboard.nextCounts(preview.new_words, preview.review_words)}</span>
                </>
              )}
            </p>
          )}
          <Link href="/lesson/vocabulary" className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl border border-brand-500/50 px-4 py-2 font-semibold text-brand-700 hover:bg-brand-500/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 dark:text-brand-100">
            <BookOpen className="size-4" aria-hidden />{openSession ? cs.lesson.resume : cs.lesson.openVocabulary}
            <KeyHint k="V" />
          </Link>
          {introduced !== null && introduced > 0 && <Link href="/check" className="ml-2 inline-flex min-h-11 items-center justify-center gap-2 rounded-xl px-4 py-2 text-sm font-semibold hover:bg-slate-100 dark:hover:bg-slate-800"><RefreshCw className="size-4" aria-hidden />{cs.check.start}</Link>}
        </section>

        {tree && !allUnits.length && <Notice>{cs.lesson.noGrammarContent}</Notice>}
        {tree && allUnits.length > 0 && (
          <div className="flex flex-col gap-3">
            <div>
              <h2 className="text-lg font-bold">{cs.lesson.allLessons}</h2>
              <p className="text-xs text-slate-500">{cs.lesson.progressIsPersonal}</p>
            </div>
            <div role="radiogroup" aria-label={cs.lesson.showLabel} className="-mx-1 flex gap-1 overflow-x-auto px-1 pb-0.5 [scrollbar-width:none]">
              {SHOWS.map((value) => {
                const n = value === "all" ? allUnits.length : allUnits.filter(SHOW_TEST[value]).length;
                return (
                  <button
                    key={value}
                    type="button"
                    role="radio"
                    aria-checked={show === value}
                    onClick={() => setShow(value)}
                    disabled={value !== "all" && n === 0}
                    className={`shrink-0 rounded-full px-2 py-1 text-sm sm:px-3 font-medium disabled:opacity-40 ${show === value ? "bg-brand-500 text-white" : "bg-slate-100 dark:bg-slate-800"}`}
                  >
                    {cs.lesson.shows[value]} {n}
                  </button>
                );
              })}
            </div>
            {LEVELS.filter((level) => !emptyLevels.includes(level)).map((level) => {
              const levelUnits = tree.levels.find((section) => section.level === level)?.units ?? [];
              const units = show === "all" ? levelUnits : levelUnits.filter(SHOW_TEST[show]);
              // A filter hides levels with no match instead of showing empty boxes.
              if (show !== "all" && units.length === 0) return null;
              // Open by default: any filtered view, the level the recommendation comes from, and
              // levels holding an open lesson or a due check. The rest start folded to their header.
              const expanded =
                show !== "all" ||
                level === focusLevel ||
                levelUnits.some((u) => u.due || u.id === tree.active_lesson_unit);
              return (
                <details key={`${level}:${show}`} open={expanded} className="group rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
                  <summary className="cursor-pointer list-none [&::-webkit-details-marker]:hidden">
                  <h3 className="mb-2 flex items-center justify-between gap-2 font-bold">
                    <span className="flex items-center gap-1.5">
                      <ChevronRight className="size-4 text-slate-400 transition-transform group-open:rotate-90" aria-hidden />
                      {level}
                    </span>
                    <span className="text-xs font-normal text-slate-500">
                      {cs.lesson.levelCoverage(levelUnits.filter((u) => u.status !== "new").length, levelUnits.length, levelUnits.filter((u) => u.status === "known" || u.status === "mastered").length)}
                    </span>
                  </h3>
                  <div className="flex h-1.5 overflow-hidden rounded-full bg-slate-100 group-open:mb-3 dark:bg-slate-800" aria-hidden>
                    <div className="bg-emerald-500" style={{ width: `${(levelUnits.filter((u) => u.status === "known" || u.status === "mastered").length / levelUnits.length) * 100}%` }} />
                    <div className="bg-sky-400" style={{ width: `${(levelUnits.filter((u) => u.status === "studied").length / levelUnits.length) * 100}%` }} />
                  </div>
                  </summary>
                    <ul className="grid gap-2 md:grid-cols-2">
                      {units.map((unit) => (
                        <li key={unit.id}>
                          <Link href={`/grammar/${unit.id}`} className="flex h-full flex-col gap-2 rounded-xl border border-slate-200 p-3 hover:border-brand-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 dark:border-slate-700">
                            {/* Title takes the full width; badges wrap under it on narrow screens
                                instead of squeezing the title into a one-word column. */}
                            <span className="flex flex-wrap items-start justify-between gap-x-2 gap-y-1">
                              <strong className="min-w-0 flex-1 basis-40">{unit.title}</strong>
                              <span className="flex shrink-0 flex-wrap items-center gap-1 text-xs">
                                {tree.active_lesson_unit === unit.id && <span className="rounded-full bg-brand-500/15 px-2 py-0.5 font-semibold text-brand-700 dark:text-brand-100">{cs.lesson.openBadge}</span>}
                                {unit.recent_errors > 0 && <span className="rounded-full bg-rose-100 px-2 py-0.5 font-semibold text-rose-800 dark:bg-rose-950 dark:text-rose-200">{cs.lesson.errorsBadge(unit.recent_errors)}</span>}
                                {unit.due && <span className="rounded-full bg-amber-100 px-2 py-0.5 font-semibold text-amber-800 dark:bg-amber-950 dark:text-amber-200">{cs.lesson.dueBadge}</span>}
                                <span className="text-slate-500">{cs.grammar.status[unit.status]}</span>
                              </span>
                            </span>
                            <span className="line-clamp-2 text-sm text-slate-600 sm:line-clamp-none dark:text-slate-300">{unit.summary}</span>
                            {/* Many topics use the same sentence as summary and objective; say it once. */}
                            {unit.objective.trim() !== unit.summary.trim() && (
                              <span className="flex items-center gap-1 text-xs text-slate-500"><CheckCircle2 className="size-3" aria-hidden />{cs.lesson.objective(unit.objective)}</span>
                            )}
                            <span className="mt-auto flex flex-wrap items-center gap-x-2 text-xs text-slate-500">
                              <span>{cs.lesson.exercises(unit.exercises)}</span>
                              {unit.checked_correct + unit.checked_errors > 0 && (
                                <span>· {cs.lesson.checkedTally(unit.checked_correct, unit.checked_correct + unit.checked_errors)}</span>
                              )}
                            </span>
                          </Link>
                        </li>
                      ))}
                    </ul>
                </details>
              );
            })}
            {/* Levels without any topic yet are one honest line, not empty boxes to open. */}
            {show === "all" && emptyLevels.length > 0 && <p className="px-1 text-sm text-slate-500">{cs.lesson.emptyLevels(emptyLevels.join(", "))}</p>}
          </div>
        )}
      </div>
    </AppShell>
  );
}
