"use client";

import { BookOpen, CheckCircle2, Eye, HelpCircle, RotateCcw, XCircle } from "lucide-react";
import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";

import { AnswerInput } from "@/components/AnswerInput";
import { GrammarNotes } from "@/components/GrammarNotes";
import { KeyHint, ShortcutLegend } from "@/components/Kbd";
import { TutorButton } from "@/components/TutorButton";
import { SessionProgress } from "@/components/SessionProgress";
import { Button, Notice } from "@/components/ui";
import {
  answerGrammar,
  completeGrammar,
  newIdempotencyKey,
  nextGrammarItem,
  revealGrammar,
  type GrammarExercise,
  type GrammarResult,
  type GrammarSession,
  type Language,
} from "@/lib/api";
import { cs } from "@/lib/i18n/cs";
import { isTypingTarget, useHotkeys } from "@/lib/keyboard";

type Phase =
  | { kind: "starting" }
  | { kind: "empty" }
  | { kind: "error"; retry: () => void }
  | { kind: "notes"; session: GrammarSession }
  | { kind: "item"; session: GrammarSession; item: GrammarExercise; result: GrammarResult | null }
  | { kind: "done"; session: GrammarSession };

const OPTION =
  "flex w-full items-center gap-3 rounded-xl border px-4 py-3 text-left text-base font-semibold outline-none focus-visible:ring-2 focus-visible:ring-brand-500 disabled:cursor-default";
const OPTION_IDLE =
  "border-slate-300 bg-white hover:border-brand-500 hover:bg-brand-50 dark:border-slate-700 dark:bg-slate-900 dark:hover:bg-slate-800";
const OPTION_RIGHT = "border-emerald-600 bg-emerald-50 text-emerald-950 dark:border-emerald-400 dark:bg-emerald-950 dark:text-emerald-50";
const OPTION_WRONG = "border-red-600 bg-red-50 text-red-950 dark:border-red-400 dark:bg-red-950 dark:text-red-50";

function kindLabel(item: GrammarExercise): string {
  if (item.kind === "translate") return cs.grammar.kind[item.direction === "target-cs" ? "translate_target" : "translate_cs"]!;
  return cs.grammar.kind[item.kind]!;
}

/** Sentence with the gap shown as a visible blank (or filled with the solution). */
function GapSentence({ prompt, fill, language }: { prompt: string; fill?: string | null; language: Language }) {
  const [before, after] = prompt.split("___");
  return (
    <p className="text-2xl font-semibold leading-relaxed" lang={language}>
      {before}
      <span
        className={`mx-1 inline-block min-w-16 border-b-2 px-1 ${
          fill ? "border-emerald-500 text-emerald-700 dark:text-emerald-300" : "border-slate-400"
        }`}
      >
        {fill ?? " "}
      </span>
      {after}
    </p>
  );
}

function Feedback({ result, mode, language }: { result: GrammarResult; mode: "learn" | "check"; language: Language }) {
  const note = result.note ? cs.feedback.notes[result.note] : null;
  const headline = (cs.feedback as Record<string, unknown>)[result.verdict];
  return (
    <div
      role="status"
      className={`flex flex-col gap-2 rounded-xl p-3 text-sm ${
        result.correct
          ? "bg-emerald-50 text-emerald-900 dark:bg-emerald-950 dark:text-emerald-100"
          : "bg-amber-50 text-amber-950 dark:bg-amber-950 dark:text-amber-100"
      }`}
    >
      <p className="flex items-center gap-2 font-semibold">
        {result.correct ? <CheckCircle2 className="size-5" aria-hidden /> : <XCircle className="size-5" aria-hidden />}
        {typeof headline === "string" ? headline : result.correct ? cs.feedback.exact : cs.feedback.wrong}
      </p>
      {note && <p>{note}</p>}
      {result.solution && (!result.correct || result.verdict !== "exact") && (
        <p>
          {cs.grammar.solution} <strong lang={language}>{result.solution}</strong>
        </p>
      )}
      {result.error && !result.correct && (
        <p className="text-xs opacity-90">
          {cs.grammar.errorKind} {cs.feedback.errors[result.error] ?? result.error}
        </p>
      )}
      {result.explanation && (
        <p>
          <span className="font-semibold">{cs.grammar.why}</span> {result.explanation}
        </p>
      )}
      {mode === "learn" && !result.task_done && <p>{cs.lesson.wrongTryAgain}</p>}
      {mode === "check" && !result.correct && <p className="text-xs opacity-80">{cs.grammar.missedNote}</p>}
    </div>
  );
}

function Tiles({
  tokens,
  placed,
  setPlaced,
  disabled,
  language,
}: {
  tokens: string[];
  placed: number[];
  setPlaced: (p: number[]) => void;
  disabled: boolean;
  language: Language;
}) {
  const remaining = tokens.map((_, i) => i).filter((i) => !placed.includes(i));
  // Backspace takes the last tile back (outside text fields).
  useEffect(() => {
    if (disabled) return;
    function onKey(e: KeyboardEvent) {
      if (e.key !== "Backspace" || isTypingTarget(e.target) || !placed.length) return;
      e.preventDefault();
      setPlaced(placed.slice(0, -1));
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [disabled, placed, setPlaced]);
  return (
    <div className="flex flex-col gap-3">
      <div
        className="flex min-h-14 flex-wrap items-center gap-2 rounded-xl border-2 border-dashed border-slate-300 p-2 dark:border-slate-700"
        aria-label={cs.grammar.kind.order}
        lang={language}
      >
        {placed.map((i, n) => (
          <button
            key={`p${i}`}
            type="button"
            disabled={disabled}
            onClick={() => setPlaced(placed.filter((_, k) => k !== n))}
            className="rounded-lg bg-brand-500 px-3 py-2 font-semibold text-white disabled:opacity-80"
          >
            {tokens[i]}
          </button>
        ))}
      </div>
      <div className="flex flex-wrap justify-center gap-2" lang={language}>
        {remaining.map((i, n) => (
          <button
            key={`r${i}`}
            type="button"
            disabled={disabled}
            data-hotkey={n < 9 ? `${n + 1}` : undefined}
            onClick={() => setPlaced([...placed, i])}
            className="flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-3 py-2 font-semibold hover:border-brand-500 dark:border-slate-700 dark:bg-slate-900"
          >
            {n < 9 && <KeyHint k={`${n + 1}`} />}
            {tokens[i]}
          </button>
        ))}
      </div>
      <p className="text-center text-xs text-slate-500">
        {cs.grammar.tilesHelp} <span className="hidden lg:inline">{cs.grammar.tilesKeys}</span>
      </p>
    </div>
  );
}

/**
 * learn: the unit's notes (a side pane on wide screens), then its exercises with retries and
 * explanations. check: due units' exercises, one attempt each.
 */
export function GrammarRunner({
  language,
  englishVariant = "uk",
  mode,
  start,
  onExit,
  exitLabel,
}: {
  language: Language;
  englishVariant?: "uk" | "us";
  mode: "learn" | "check";
  start: () => Promise<{ session: GrammarSession | null }>;
  onExit: () => void;
  exitLabel: string;
}) {
  const [phase, setPhase] = useState<Phase>({ kind: "starting" });
  const [text, setText] = useState("");
  const [placed, setPlaced] = useState<number[]>([]);
  const [chosen, setChosen] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [netError, setNetError] = useState(false);
  const pendingKey = useRef<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const run = useRef(0);
  useHotkeys();

  const advance = useCallback(async (session: GrammarSession) => {
    const id = run.current;
    try {
      const { item } = await nextGrammarItem(session.id);
      if (id !== run.current) return;
      setText("");
      setPlaced([]);
      setChosen(null);
      pendingKey.current = null;
      if (item) setPhase({ kind: "item", session, item, result: null });
      else {
        const done = await completeGrammar(session.id);
        if (id === run.current) setPhase({ kind: "done", session: done });
      }
    } catch {
      if (id === run.current) setPhase({ kind: "error", retry: () => void advance(session) });
    }
  }, []);

  const begin = useCallback(async () => {
    const id = ++run.current;
    setPhase({ kind: "starting" });
    try {
      const { session } = await start();
      if (id !== run.current) return;
      if (!session) setPhase({ kind: "empty" });
      else if (mode === "learn" && session.remaining === session.total) setPhase({ kind: "notes", session });
      else await advance(session);
    } catch {
      if (id === run.current) setPhase({ kind: "error", retry: () => void begin() });
    }
  }, [start, mode, advance]);

  useEffect(() => {
    void begin();
  }, [begin]);

  useEffect(() => {
    if (phase.kind === "item" && !phase.result?.task_done && (phase.item.kind === "gap" || phase.item.kind === "translate"))
      inputRef.current?.focus();
  }, [phase]);

  const unit = phase.kind === "notes" || phase.kind === "item" || phase.kind === "done" ? phase.session.unit : null;
  const notesPane = unit ? (
    <aside className="hidden lg:sticky lg:top-4 lg:block lg:max-h-[calc(100vh-2rem)] lg:overflow-y-auto lg:rounded-2xl lg:border lg:border-slate-200 lg:p-5 dark:lg:border-slate-800">
      <GrammarNotes
        unit={unit}
        language={language}
        englishVariant={englishVariant}
        header={
          <h2 className="flex items-center gap-2 text-sm font-semibold text-slate-500">
            <BookOpen className="size-4" aria-hidden /> {cs.grammar.notes} · {unit.level}
          </h2>
        }
      />
    </aside>
  ) : null;
  const wrap = (body: React.ReactNode) =>
    notesPane ? (
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)] lg:items-start">
        {notesPane}
        <div className="mx-auto w-full max-w-xl">{body}</div>
      </div>
    ) : (
      <div className="mx-auto w-full max-w-xl">{body}</div>
    );

  if (phase.kind === "starting") return <p className="text-center text-slate-500">{cs.grammar.preparing}</p>;
  if (phase.kind === "empty")
    return (
      <div className="mx-auto flex w-full max-w-xl flex-col gap-4">
        <Notice>{cs.grammar.checkNothing}</Notice>
        <Button variant="secondary" onClick={onExit}>
          {exitLabel}
        </Button>
      </div>
    );
  if (phase.kind === "error")
    return (
      <div className="mx-auto flex w-full max-w-xl flex-col gap-4">
        <Notice tone="error">{cs.common.offline}</Notice>
        <Button onClick={phase.retry}>{cs.common.retry}</Button>
      </div>
    );
  if (phase.kind === "notes") {
    const { session } = phase;
    return wrap(
      <div className="flex flex-col gap-4">
        <h2 className="text-2xl font-bold">{session.unit!.title}</h2>
        <div className="lg:hidden">
          <GrammarNotes unit={session.unit!} language={language} englishVariant={englishVariant} />
        </div>
        <p className="hidden text-slate-600 lg:block dark:text-slate-300">{session.unit!.summary}</p>
        <Notice>{cs.lesson.learnHelp}</Notice>
        <Button data-hotkey="enter" autoFocus onClick={() => void advance(session)}>
          {cs.grammar.toPractice} <KeyHint k="Enter" />
        </Button>
      </div>,
    );
  }
  if (phase.kind === "done") {
    const s = phase.session.summary;
    const tiles: [string, string | number][] =
      mode === "check"
        ? [
            [cs.grammar.summaryCorrect, `${s.first_try_correct ?? 0} / ${s.total ?? 0}`],
            [cs.grammar.summaryRemediation, s.remediation ?? 0],
          ]
        : [
            [cs.grammar.summaryPracticed, s.total ?? 0],
            [cs.grammar.summaryRemediation, s.remediation ?? 0],
          ];
    return wrap(
      <div className="flex flex-col gap-4">
        <h2 className="text-xl font-bold">{mode === "check" ? cs.grammar.doneCheck : cs.grammar.doneLesson}</h2>
        <dl className="grid grid-cols-2 gap-2 text-sm">
          {tiles.map(([label, value]) => (
            <div key={label} className="rounded-xl bg-slate-50 p-3 dark:bg-slate-800/60">
              <dt className="text-xs text-slate-500">{label}</dt>
              <dd className="text-xl font-bold tabular-nums">{value}</dd>
            </div>
          ))}
        </dl>
        {mode === "learn" && <Notice>{cs.grammar.studiedNote}</Notice>}
        <div className="flex flex-col gap-2 sm:flex-row">
          {mode === "check" && (
            <Button className="flex-1" onClick={() => void begin()}>
              {cs.grammar.another}
            </Button>
          )}
          <Button variant={mode === "check" ? "secondary" : "primary"} className="flex-1" onClick={onExit} autoFocus data-hotkey="enter">
            {exitLabel}
          </Button>
        </div>
      </div>,
    );
  }

  const { session, item, result } = phase;
  const finished = result?.task_done ?? false;
  const targetLang: Language | "cs" = item.kind === "translate" && item.direction === "target-cs" ? "cs" : language;

  async function send(body: { choice?: number; text?: string } | "reveal") {
    if (busy) return;
    if (body !== "reveal" && body.choice !== undefined) {
      if (body.choice !== chosen) pendingKey.current = null;
      setChosen(body.choice);
    }
    setBusy(true);
    setNetError(false);
    try {
      pendingKey.current ??= newIdempotencyKey();
      const r =
        body === "reveal"
          ? await revealGrammar(item.item_id, pendingKey.current)
          : await answerGrammar(item.item_id, { idempotency_key: pendingKey.current, ...body });
      pendingKey.current = null;
      setPhase({ kind: "item", session, item, result: r });
    } catch {
      setNetError(true);
    } finally {
      setBusy(false);
    }
  }

  const answerText = item.kind === "order" ? placed.map((i) => item.tokens![i]).join(" ") : text;
  function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (finished) void advance(session);
    else if (answerText.trim()) {
      pendingKey.current = null; // a changed text is a new attempt
      void send({ text: answerText });
    }
  }

  const legend: [string, string][] = finished
    ? [["Enter", cs.lesson.next], ["W", cs.keys.why]]
    : item.kind === "choice"
      ? [[`1–${item.options!.length}`, cs.keys.choose], ["N", cs.keys.reveal]]
      : item.kind === "order"
        ? [["1–9", cs.grammar.kind.order!], ["⌫", cs.grammar.clear], ["Enter", cs.keys.submit]]
        : [["Enter", cs.keys.submit], ["Alt+N", cs.keys.reveal]];

  return wrap(
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-end gap-2 text-xs text-slate-500">
        <span className="rounded-full bg-slate-100 px-2 py-0.5 text-slate-600 dark:bg-slate-800 dark:text-slate-300">
          {item.is_remediation ? (
            <span className="inline-flex items-center gap-1">
              <RotateCcw className="size-3" aria-hidden /> {cs.grammar.remediation}
            </span>
          ) : mode === "check" ? (
            cs.check.title
          ) : (
            item.unit_title
          )}
        </span>
      </div>
      <SessionProgress current={item.position + 1} total={item.total} label={cs.grammar.exercise(item.position + 1, item.total)} />

      <section className="flex flex-col gap-2 rounded-2xl border border-slate-200 bg-white p-5 text-center shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <p className="text-sm text-slate-500">{kindLabel(item)}</p>
        {item.kind === "choice" || item.kind === "gap" ? (
          <GapSentence prompt={item.prompt} fill={result?.expected && finished ? result.expected : null} language={language} />
        ) : (
          <p className="text-2xl font-semibold" lang={item.kind === "translate" && item.direction === "target-cs" ? language : "cs"}>
            {item.prompt}
          </p>
        )}
        {item.prompt_cs && (
          <p className="text-sm text-slate-500" lang="cs">
            {item.prompt_cs}
          </p>
        )}
        {mode === "check" && item.unit_title && <p className="text-xs text-slate-400">{item.unit_title}</p>}
      </section>

      {item.kind === "choice" ? (
        <div className="grid gap-2 sm:grid-cols-2">
          {item.options!.map((o, i) => {
            const right = result?.expected === o && (finished || mode === "learn");
            const wrong = chosen === i && result && !result.correct;
            return (
              <button
                key={`${item.item_id}:${i}`}
                type="button"
                data-hotkey={i < 9 ? `${i + 1}` : undefined}
                disabled={busy || finished}
                onClick={() => void send({ choice: i })}
                className={`${OPTION} ${right ? OPTION_RIGHT : wrong ? OPTION_WRONG : OPTION_IDLE}`}
                lang={language}
              >
                {i < 9 && <KeyHint k={`${i + 1}`} />}
                <span className="flex-1">{o}</span>
                {right && <CheckCircle2 className="size-5" aria-hidden />}
                {wrong && <XCircle className="size-5" aria-hidden />}
              </button>
            );
          })}
        </div>
      ) : (
        <form onSubmit={onSubmit} className="flex flex-col gap-2">
          {item.kind === "order" ? (
            <Tiles tokens={item.tokens!} placed={placed} setPlaced={setPlaced} disabled={busy || finished} language={language} />
          ) : (
            <AnswerInput
              ref={inputRef}
              language={targetLang}
              value={text}
              onChange={setText}
              disabled={busy || finished}
              showChars={targetLang !== "cs"}
            />
          )}
          {!finished && (
            <Button type="submit" disabled={busy || !answerText.trim()}>
              {cs.lesson.check} <KeyHint k="Enter" />
            </Button>
          )}
        </form>
      )}

      {result && <Feedback result={result} mode={mode} language={language} />}
      {finished && <TutorButton key={item.item_id} kind="grammar" id={item.item_id} />}
      {netError && <Notice tone="error">{cs.common.offline}</Notice>}

      {finished ? (
        <Button onClick={() => void advance(session)} autoFocus data-hotkey="enter">
          {cs.lesson.next} <KeyHint k="Enter" />
        </Button>
      ) : (
        <Button variant="ghost" disabled={busy} onClick={() => void send("reveal")} data-hotkey="reveal">
          {mode === "check" ? <HelpCircle className="size-4" aria-hidden /> : <Eye className="size-4" aria-hidden />}
          {mode === "check" ? cs.check.dontKnow : cs.lesson.reveal}
        </Button>
      )}
      <ShortcutLegend items={legend} />
      {unit && (
        <details className="rounded-xl text-sm lg:hidden">
          <summary className="flex cursor-pointer items-center gap-2 text-slate-500">
            <BookOpen className="size-4" aria-hidden /> {cs.grammar.backToNotes}
          </summary>
          <div className="mt-2">
            <GrammarNotes unit={unit} language={language} englishVariant={englishVariant} />
          </div>
        </details>
      )}
    </div>,
  );
}
