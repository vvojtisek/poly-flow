"use client";

import { BookOpen, CheckCircle2, Compass, Gauge, GraduationCap, PlayCircle, RefreshCw } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { AppShell, FullPageStatus, LanguagePicker } from "@/components/AppShell";
import { Button, Notice } from "@/components/ui";
import { PlayButton } from "@/components/PlayButton";
import { getDiagnosticInfo, getGrammarTree, getGrammarUnit, getLessonPreview, grammarExampleAudioUrl, getProgress, type CefrLevel, type GrammarTree, type LessonPreview, type LevelBadge } from "@/lib/api";
import { useRequireMe } from "@/lib/auth";
import { isTypingTarget, useHotkeys } from "@/lib/keyboard";
import { KeyHint } from "@/components/Kbd";
import { cs } from "@/lib/i18n/cs";

const PRIMARY = "mt-4 inline-flex min-h-11 items-center justify-center gap-2 rounded-xl bg-brand-500 px-4 py-2 font-semibold text-white hover:bg-brand-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2";
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
  const [tree, setTree] = useState<GrammarTree | null>(null);
  const [placement, setPlacement] = useState<string | null>(null);
  const [badge, setBadge] = useState<string | null>(null);
  const [introduced, setIntroduced] = useState<number | null>(null);
  const [failed, setFailed] = useState(false);
  const [openSession, setOpenSession] = useState(false);
  const [estimate, setEstimate] = useState<{ level: string; at: string | null; source: "test" | "progress" } | null>(null);
  const [testOpen, setTestOpen] = useState(false);
  const [testAvailable, setTestAvailable] = useState(false);
  const [preview, setPreview] = useState<LessonPreview | null>(null);

  useEffect(() => {
    if (!language) return;
    let live = true;
    setTree(null);
    setFailed(false);
    setPreview(null);
    setOpenSession(false);
    // The grammar tree is the page; the estimate, progress and lesson preview only refine it, so
    // one of them failing must not blank the whole overview.
    Promise.allSettled([getGrammarTree(language), getDiagnosticInfo(language), getProgress(language), getLessonPreview(language)]).then(
      ([grammar, assessment, progress, next]) => {
        if (!live) return;
        if (grammar.status === "rejected") {
          setFailed(true);
          return;
        }
        setTree(grammar.value);
        const p = progress.status === "fulfilled" ? progress.value : null;
        const a = assessment.status === "fulfilled" ? assessment.value : null;
        setPlacement(a?.latest?.level ?? p?.cefr_level ?? null);
        setEstimate(
          a?.latest ? { level: a.latest.level, at: a.latest.decided_at, source: "test" } : p?.cefr_level ? { level: p.cefr_level, at: null, source: "progress" } : null,
        );
        setTestOpen(Boolean(a?.active_session_id));
        setTestAvailable(Boolean(a?.available));
        setBadge(p ? highestBadge(p.level_badges) : null);
        setIntroduced(p?.introduced ?? null);
        setOpenSession(Boolean(p?.active_session_id));
        if (next.status === "fulfilled") setPreview(next.value);
      },
    );
    return () => {
      live = false;
    };
  }, [language, me?.acting.id]);

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
  const allUnits = tree?.levels.flatMap((section) => section.units) ?? [];
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
            {estimate
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
        {failed && <Notice tone="error">{cs.common.error}</Notice>}
        {!tree && !failed && <p className="text-sm text-slate-500">{cs.common.loading}</p>}

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

        {tree && (
          <div className="flex flex-col gap-3">
            <div>
              <h2 className="text-lg font-bold">{cs.lesson.allLessons}</h2>
              <p className="text-xs text-slate-500">{cs.lesson.progressIsPersonal}</p>
            </div>
            {LEVELS.map((level) => {
              const units = tree.levels.find((section) => section.level === level)?.units ?? [];
              return (
                <section key={level} className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
                  <h3 className="mb-3 flex items-center justify-between gap-2 font-bold">
                    <span>{level}</span>
                    <span className="text-xs font-normal text-slate-500">
                      {units.length ? cs.lesson.levelCoverage(units.filter((u) => u.status !== "new").length, units.length, units.filter((u) => u.status === "known" || u.status === "mastered").length) : cs.lesson.notAvailable}
                    </span>
                  </h3>
                  {units.length > 0 && (
                    <div className="-mt-1 mb-3 flex h-1.5 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800" aria-hidden>
                      <div className="bg-emerald-500" style={{ width: `${(units.filter((u) => u.status === "known" || u.status === "mastered").length / units.length) * 100}%` }} />
                      <div className="bg-sky-400" style={{ width: `${(units.filter((u) => u.status === "studied").length / units.length) * 100}%` }} />
                    </div>
                  )}
                  {units.length ? (
                    <ul className="grid gap-2 md:grid-cols-2">
                      {units.map((unit) => (
                        <li key={unit.id}>
                          <Link href={`/grammar/${unit.id}`} className="flex h-full flex-col gap-2 rounded-xl border border-slate-200 p-3 hover:border-brand-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 dark:border-slate-700">
                            <span className="flex items-center justify-between gap-2">
                              <strong>{unit.title}</strong>
                              <span className="flex shrink-0 items-center gap-1 text-xs">
                                {tree.active_lesson_unit === unit.id && <span className="rounded-full bg-brand-500/15 px-2 py-0.5 font-semibold text-brand-700 dark:text-brand-100">{cs.lesson.openBadge}</span>}
                                {unit.due && <span className="rounded-full bg-amber-100 px-2 py-0.5 font-semibold text-amber-800 dark:bg-amber-950 dark:text-amber-200">{cs.lesson.dueBadge}</span>}
                                <span className="text-slate-500">{cs.grammar.status[unit.status]}</span>
                              </span>
                            </span>
                            <span className="text-sm text-slate-600 dark:text-slate-300">{unit.summary}</span>
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
                  ) : <p className="text-sm text-slate-500">{cs.lesson.levelNotImplemented}</p>}
                </section>
              );
            })}
            {!allUnits.length && <Notice>{cs.lesson.noGrammarContent}</Notice>}
          </div>
        )}
      </div>
    </AppShell>
  );
}
