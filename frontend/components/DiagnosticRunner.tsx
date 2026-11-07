"use client";

import { BookOpenText, CheckCircle2, Headphones, Languages, MessageSquareQuote, Puzzle, XCircle } from "lucide-react";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { KeyHint, ShortcutLegend } from "@/components/Kbd";
import { OPTION_BASE, OPTION_STATES } from "@/components/LessonRunner";
import { PlayButton } from "@/components/PlayButton";
import { SessionProgress } from "@/components/SessionProgress";
import { Button, Notice } from "@/components/ui";
import {
  answerDiagnostic,
  diagnosticAudioUrl,
  getDiagnostic,
  startDiagnostic,
  stopDiagnostic,
  type DiagnosticAnswer,
  type DiagnosticBand,
  type DiagnosticResult,
  type DiagnosticSkill,
  type DiagnosticState,
  type Language,
} from "@/lib/api";
import { cs } from "@/lib/i18n/cs";
import { englishVariantText } from "@/lib/english-variant";
import { useHotkeys } from "@/lib/keyboard";

const BANDS: DiagnosticBand[] = ["A1", "A2", "B1", "B2", "B2+"];
const SKILL_ICON: Record<DiagnosticSkill, typeof Puzzle> = {
  grammar: Puzzle,
  vocabulary: Languages,
  reading: BookOpenText,
  listening: Headphones,
  idiom: MessageSquareQuote,
};

/** theta (-3..3) as a share of the A1..B2+ track; band b sits at difficulty index - 2. */
function trackShare(theta: number): number {
  return Math.min(1, Math.max(0, (theta + 2.5) / 5));
}

/** The A1..B2+ ladder with the band being probed and a marker for the running estimate. */
export function BandLadder({ band, theta, compact = false }: { band?: DiagnosticBand; theta: number; compact?: boolean }) {
  return (
    <div className="flex flex-col gap-1" aria-hidden={compact}>
      <div className="relative grid grid-cols-5 gap-1">
        {BANDS.map((b) => (
          <div
            key={b}
            className={`rounded-lg py-1.5 text-center text-xs font-bold motion-safe:transition-colors ${
              b === band
                ? "bg-brand-500 text-white shadow-sm"
                : "bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400"
            }`}
          >
            {b}
          </div>
        ))}
      </div>
      <div className="relative h-2 rounded-full bg-gradient-to-r from-emerald-200 via-amber-200 to-rose-200 dark:from-emerald-900 dark:via-amber-900 dark:to-rose-900">
        <span
          className="absolute top-1/2 size-3.5 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-white bg-brand-600 shadow motion-safe:transition-[left] motion-safe:duration-500 dark:border-slate-900"
          style={{ left: `${trackShare(theta) * 100}%` }}
        />
      </div>
    </div>
  );
}

type Phase =
  | { kind: "loading" }
  | { kind: "error" }
  | { kind: "question"; state: DiagnosticState; chosen: string | null; feedback: DiagnosticAnswer | null; busy: boolean }
  | { kind: "done"; state: DiagnosticState };

export function DiagnosticRunner({ language, englishVariant = "uk", onAgain }: { language: Language; englishVariant?: "uk" | "us"; onAgain: () => void }) {
  const [phase, setPhase] = useState<Phase>({ kind: "loading" });
  useHotkeys(phase.kind === "question" || phase.kind === "done");

  const show = useCallback((state: DiagnosticState) => {
    if (state.question) setPhase({ kind: "question", state, chosen: null, feedback: null, busy: false });
    else setPhase({ kind: "done", state });
  }, []);

  useEffect(() => {
    let cancelled = false;
    startDiagnostic(language)
      .then((s) => !cancelled && show(s))
      .catch(() => !cancelled && setPhase({ kind: "error" }));
    return () => {
      cancelled = true;
    };
  }, [language, show]);

  async function choose(choice: string | null) {
    if (phase.kind !== "question" || phase.busy || phase.feedback) return;
    const q = phase.state.question!;
    setPhase({ ...phase, chosen: choice, busy: true });
    try {
      const fb = await answerDiagnostic(phase.state.session_id, q.position, choice);
      setPhase({ ...phase, chosen: choice, feedback: fb, busy: false });
    } catch {
      setPhase({ kind: "error" });
    }
  }

  async function next() {
    if (phase.kind !== "question") return;
    setPhase({ ...phase, busy: true });
    try {
      show(await getDiagnostic(phase.state.session_id));
    } catch {
      setPhase({ kind: "error" });
    }
  }

  async function stop() {
    if (phase.kind !== "question") return;
    setPhase({ ...phase, busy: true });
    try {
      show(await stopDiagnostic(phase.state.session_id));
    } catch {
      setPhase({ kind: "error" });
    }
  }

  if (phase.kind === "loading") return <p className="text-center text-slate-500">{cs.cefr.preparing}</p>;
  if (phase.kind === "error") return <Notice tone="error">{cs.common.offline}</Notice>;
  if (phase.kind === "done")
    return <DiagnosticDone result={phase.state.result} onAgain={onAgain} />;

  const { state, chosen, feedback, busy } = phase;
  const q = state.question!;
  const Icon = SKILL_ICON[q.skill];
  const theta = feedback?.theta ?? q.theta;
  return (
    <div className="flex flex-col gap-4">
      <div className="flex justify-end text-sm text-slate-500">
        <button type="button" className="underline-offset-2 hover:underline" onClick={() => void stop()} disabled={busy}>
          {cs.cefr.stop}
        </button>
      </div>
      <SessionProgress current={q.asked + 1} total={q.max_items} upperBound label={cs.cefr.question(q.asked + 1, q.max_items)} />
      <div className="flex flex-col gap-1">
        <p className="text-xs text-slate-500">{cs.cefr.probing}</p>
        <BandLadder band={q.band} theta={theta} />
      </div>

      <section className="flex flex-col gap-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-brand-600 dark:text-brand-50">
          <Icon className="size-4" aria-hidden />
          {cs.cefr.skillName[q.skill]}
        </p>
        {q.context && (
          <blockquote lang={language} className="rounded-xl bg-slate-50 p-3 text-base leading-relaxed text-slate-800 dark:bg-slate-800 dark:text-slate-100">
            {language === "en" ? englishVariantText(q.context, englishVariant) : q.context}
          </blockquote>
        )}
        {q.has_audio && (
          <div className="flex items-center gap-3 rounded-xl bg-brand-500/5 p-3">
            <PlayButton url={diagnosticAudioUrl(state.session_id, q.position)} label={cs.cefr.listenAgain} hotkey />
            <p className="text-sm text-slate-600 dark:text-slate-300">{cs.cefr.listen}</p>
          </div>
        )}
        <p className="text-lg font-semibold" lang={q.skill === "grammar" || q.skill === "vocabulary" ? language : "cs"}>
          {language === "en" ? englishVariantText(q.prompt, englishVariant) : q.prompt}
        </p>
      </section>

      <div className="grid gap-2">
        {q.options.map((o, i) => {
          const state = !feedback
            ? chosen === o && busy
              ? "pending"
              : "idle"
            : o === feedback.answer
              ? "correct"
              : o === chosen
                ? "wrong"
                : "muted";
          return (
            <button
              key={`${q.position}:${o}`}
              type="button"
              data-hotkey={i < 9 ? `${i + 1}` : undefined}
              className={`${OPTION_BASE} ${OPTION_STATES[state]}`}
              disabled={busy || !!feedback}
              onClick={() => void choose(o)}
              lang={language}
            >
              <span className="flex items-center gap-3">
                {i < 9 && <KeyHint k={`${i + 1}`} />}
                {language === "en" ? englishVariantText(o, englishVariant) : o}
              </span>
              {state === "correct" && <CheckCircle2 className="size-5 shrink-0" aria-hidden />}
              {state === "wrong" && <XCircle className="size-5 shrink-0" aria-hidden />}
            </button>
          );
        })}
        {!feedback && (
          <Button variant="ghost" data-hotkey="reveal" disabled={busy} onClick={() => void choose(null)}>
            {cs.cefr.dontKnow} <KeyHint k="N" />
          </Button>
        )}
      </div>

      {feedback && (
        <div
          role="status"
          className={`flex flex-col gap-2 rounded-xl p-3 text-sm ${
            feedback.correct
              ? "bg-emerald-50 text-emerald-900 dark:bg-emerald-950 dark:text-emerald-100"
              : "bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-100"
          }`}
        >
          <p className="font-semibold">
            {feedback.correct ? cs.cefr.correct : feedback.dont_know ? cs.cefr.dontKnowNote : cs.cefr.wrong}
            {!feedback.correct && <span lang={language}> {language === "en" ? englishVariantText(feedback.answer, englishVariant) : feedback.answer}</span>}
          </p>
          <p>{feedback.explain}</p>
          {feedback.transcript && (
            <p className="text-xs opacity-80">
              {cs.cefr.transcript}: <span lang={language}>{language === "en" ? englishVariantText(feedback.transcript, englishVariant) : feedback.transcript}</span>
            </p>
          )}
          <Button className="mt-1" autoFocus data-hotkey="enter" disabled={busy} onClick={() => void next()}>
            {cs.cefr.next} <KeyHint k="Enter" />
          </Button>
        </div>
      )}
      <ShortcutLegend
        items={[
          ["1–4", cs.keys.choose],
          ["N", cs.cefr.dontKnow],
          ...(q.has_audio ? ([["P", cs.audio.play]] as [string, string][]) : []),
          ["Enter", cs.cefr.next],
        ]}
      />
    </div>
  );
}

export function DiagnosticDone({ result, onAgain }: { result: DiagnosticResult | null; onAgain: () => void }) {
  const router = useRouter();
  if (!result || !result.placed)
    return (
      <div className="flex flex-col gap-3">
        <Notice>{cs.cefr.notPlaced}</Notice>
        <Button onClick={onAgain}>{cs.cefr.again}</Button>
      </div>
    );
  const level = result.level ?? "pre-A1";
  return (
    <div className="flex flex-col gap-4">
      <section className="flex flex-col items-center gap-2 rounded-2xl border border-brand-500/40 bg-brand-500/5 p-5 text-center motion-safe:animate-pop-in">
        <p className="text-xs uppercase tracking-wide text-slate-500">{cs.cefr.doneTitle}</p>
        <p className="text-5xl font-black text-brand-600 dark:text-brand-50">{level === "pre-A1" ? "A0" : level}</p>
        <p className="text-lg font-semibold">{cs.cefr.levelName[level]}</p>
        {result.low && result.high && <p className="text-sm text-slate-500">{cs.cefr.range(result.low, result.high)}</p>}
        {result.next && <p className="text-sm text-slate-600 dark:text-slate-300">{cs.cefr.nextGoal(result.next)}</p>}
        <div className="mt-2 w-full max-w-sm">
          <BandLadder band={level === "pre-A1" ? undefined : level} theta={result.theta ?? -2.5} compact />
        </div>
      </section>

      {!!result.bands?.length && (
        <section className="flex flex-col gap-2">
          <h3 className="text-sm font-semibold text-slate-600 dark:text-slate-300">{cs.cefr.ladder}</h3>
          <div className="grid grid-cols-5 gap-1">
            {BANDS.map((b) => {
              const r = result.bands!.find((x) => x.band === b);
              const share = r && r.asked ? r.correct / r.asked : null;
              return (
                <div key={b} className="flex flex-col items-center gap-1">
                  <div className="flex h-20 w-full items-end overflow-hidden rounded-lg bg-slate-100 dark:bg-slate-800">
                    <div
                      className={`w-full ${share === null ? "" : share >= 0.65 ? "bg-emerald-500" : share >= 0.4 ? "bg-amber-400" : "bg-rose-400"}`}
                      style={{ height: `${share === null ? 0 : Math.max(6, share * 100)}%` }}
                    />
                  </div>
                  <span className="text-xs font-bold">{b}</span>
                  <span className="text-[0.7rem] text-slate-500">{r ? `${r.correct}/${r.asked}` : "–"}</span>
                </div>
              );
            })}
          </div>
        </section>
      )}

      {!!result.skills?.length && (
        <section className="flex flex-col gap-2">
          <h3 className="text-sm font-semibold text-slate-600 dark:text-slate-300">{cs.cefr.skills}</h3>
          <ul className="flex flex-col gap-1">
            {result.skills.map((s) => {
              const Icon = SKILL_ICON[s.skill];
              const tone =
                s.verdict === "strong"
                  ? "text-emerald-700 dark:text-emerald-300"
                  : s.verdict === "weak"
                    ? "text-rose-700 dark:text-rose-300"
                    : "text-slate-500";
              return (
                <li key={s.skill} className="flex items-center justify-between gap-2 rounded-lg bg-slate-50 px-3 py-2 text-sm dark:bg-slate-800/60">
                  <span className="flex items-center gap-2">
                    <Icon className="size-4 text-brand-500" aria-hidden />
                    {cs.cefr.skillName[s.skill]}
                  </span>
                  <span className="flex items-center gap-3">
                    <span className="tabular-nums text-slate-500">
                      {s.correct}/{s.asked}
                    </span>
                    <span className={`text-xs font-semibold ${tone}`}>{cs.cefr.verdict[s.verdict]}</span>
                  </span>
                </li>
              );
            })}
          </ul>
        </section>
      )}

      <div className="flex flex-col gap-1 text-sm text-slate-600 dark:text-slate-300">
        <p>{cs.cefr.unlockedGrammar(result.grammar_queued ?? 0)}</p>
        {(result.grammar_returned ?? 0) > 0 && <p>{cs.cefr.returnedGrammar(result.grammar_returned ?? 0)}</p>}
        {!!result.exams_opened?.length && <p>{cs.cefr.examsOpened(result.exams_opened)}</p>}
      </div>
      <p className="text-xs text-slate-500">{cs.cefr.honest}</p>
      <div className="flex flex-col gap-2 sm:flex-row">
        <Button className="flex-1" autoFocus data-hotkey="enter" onClick={() => router.push("/grammar")}>
          {cs.cefr.toGrammar}
        </Button>
        <Button variant="secondary" className="flex-1" onClick={() => router.push("/levels")}>
          {cs.cefr.toLevels}
        </Button>
        <Button variant="ghost" className="flex-1" onClick={onAgain}>
          {cs.cefr.again}
        </Button>
      </div>
    </div>
  );
}
