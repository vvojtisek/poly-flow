"use client";

import { CheckCircle2, Eye, Lightbulb, XCircle } from "lucide-react";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";

import { Button, Notice } from "@/components/ui";
import {
  completeLesson,
  newIdempotencyKey,
  nextTask,
  requestHint,
  revealAnswer,
  startLesson,
  submitAnswer,
  type AnswerResult,
  type Language,
  type LessonSession,
  type Task,
} from "@/lib/api";
import { cs } from "@/lib/i18n/cs";

const SPECIAL_CHARS: Record<Language, string[]> = {
  de: ["ä", "ö", "ü", "ß", "Ä", "Ö", "Ü"],
  fr: ["é", "è", "ê", "à", "â", "ç", "ô", "î", "û", "ù", "ë", "œ"],
  it: ["à", "è", "é", "ì", "ò", "ù"],
};

type Phase =
  | { kind: "starting" }
  | { kind: "empty" }
  | { kind: "error"; retry: () => void }
  | { kind: "task"; session: LessonSession; task: Task; result: AnswerResult | null }
  | { kind: "done"; session: LessonSession };

function Feedback({ result }: { result: AnswerResult }) {
  const good = result.correct;
  const note = result.note ? cs.feedback.notes[result.note] : null;
  return (
    <div
      role="status"
      className={`flex flex-col gap-1 rounded-xl p-3 text-sm ${
        good
          ? "bg-emerald-50 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-100"
          : "bg-amber-50 text-amber-900 dark:bg-amber-950 dark:text-amber-100"
      }`}
    >
      <p className="flex items-center gap-2 font-semibold">
        {good ? <CheckCircle2 className="size-5" aria-hidden /> : <XCircle className="size-5" aria-hidden />}
        {cs.feedback[result.verdict]}
      </p>
      {note && <p>{note}</p>}
      {result.expected && (
        <p>
          {cs.lesson.expected} <strong>{result.expected}</strong>
          {result.meaning && result.meaning !== result.expected && (
            <>
              {" "}
              · {cs.lesson.meaning} {result.meaning}
            </>
          )}
        </p>
      )}
      {result.task_done && !result.counted && <p className="text-xs opacity-80">{cs.lesson.notCounted}</p>}
    </div>
  );
}

export function LessonRunner({ language }: { language: Language }) {
  const router = useRouter();
  const [phase, setPhase] = useState<Phase>({ kind: "starting" });
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [netError, setNetError] = useState(false);
  // Reused until the server answers, so a retried request cannot double-count.
  const pendingKey = useRef<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const advance = useCallback(async (session: LessonSession) => {
    try {
      const { task } = await nextTask(session.id);
      setText("");
      pendingKey.current = null;
      if (task) setPhase({ kind: "task", session, task, result: null });
      else setPhase({ kind: "done", session: await completeLesson(session.id) });
    } catch {
      setPhase({ kind: "error", retry: () => void advance(session) });
    }
  }, []);

  const begin = useCallback(async () => {
    setPhase({ kind: "starting" });
    try {
      const { session } = await startLesson(language);
      if (!session) setPhase({ kind: "empty" });
      else await advance(session);
    } catch {
      setPhase({ kind: "error", retry: () => void begin() });
    }
  }, [language, advance]);

  useEffect(() => {
    void begin();
  }, [begin]);

  useEffect(() => {
    if (phase.kind === "task" && phase.task.type === "recall" && !phase.result?.task_done) {
      inputRef.current?.focus();
    }
  }, [phase]);

  if (phase.kind === "starting") return <p className="text-center text-slate-500">{cs.lesson.preparing}</p>;
  if (phase.kind === "empty")
    return (
      <div className="flex flex-col gap-4">
        <Notice>{cs.lesson.empty}</Notice>
        <Button variant="secondary" onClick={() => router.push("/")}>
          {cs.lesson.toDashboard}
        </Button>
      </div>
    );
  if (phase.kind === "error")
    return (
      <div className="flex flex-col gap-4">
        <Notice tone="error">{cs.common.offline}</Notice>
        <Button onClick={phase.retry}>{cs.common.retry}</Button>
      </div>
    );
  if (phase.kind === "done") {
    const s = phase.session.summary;
    return (
      <div className="flex flex-col gap-4">
        <h2 className="text-xl font-bold">{cs.lesson.doneTitle}</h2>
        <dl className="grid grid-cols-2 gap-2 text-sm">
          {(
            [
              [cs.lesson.summaryFirstTry, `${s.first_try_correct ?? 0} / ${s.total ?? 0}`],
              [cs.lesson.summaryNew, s.new_items ?? 0],
              [cs.lesson.summaryReviewed, s.reviewed_items ?? 0],
              [cs.lesson.summaryRevealed, s.revealed ?? 0],
            ] as const
          ).map(([label, value]) => (
            <div key={label} className="rounded-xl bg-slate-50 p-3 dark:bg-slate-800/60">
              <dt className="text-xs text-slate-500">{label}</dt>
              <dd className="text-xl font-bold tabular-nums">{value}</dd>
            </div>
          ))}
        </dl>
        <div className="flex flex-col gap-2 sm:flex-row">
          <Button className="flex-1" onClick={() => void begin()}>
            {cs.lesson.another}
          </Button>
          <Button variant="secondary" className="flex-1" onClick={() => router.push("/")}>
            {cs.lesson.toDashboard}
          </Button>
        </div>
      </div>
    );
  }

  const { session, task, result } = phase;
  const finished = result?.task_done ?? false;

  async function send(body: { choice?: number; text?: string } | "reveal") {
    if (busy) return;
    setBusy(true);
    setNetError(false);
    pendingKey.current ??= newIdempotencyKey();
    try {
      const r =
        body === "reveal"
          ? await revealAnswer(task.id, pendingKey.current)
          : await submitAnswer(task.id, { idempotency_key: pendingKey.current, ...body });
      pendingKey.current = null;
      setPhase({ kind: "task", session, task, result: r });
    } catch {
      setNetError(true); // the key is kept, so pressing again resends the same attempt
    } finally {
      setBusy(false);
    }
  }

  async function hint() {
    try {
      setPhase({ kind: "task", session, task: await requestHint(task.id), result });
    } catch {
      setNetError(true);
    }
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (finished) void advance(session);
    else if (text.trim()) void send({ text });
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between text-xs text-slate-500">
        <span>{cs.lesson.progress(task.position + 1, task.total)}</span>
        <span className="rounded-full bg-slate-100 px-2 py-0.5 dark:bg-slate-800">
          {task.is_new_item ? cs.lesson.newWord : cs.lesson.review}
        </span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-800">
        <div className="h-full bg-brand-500" style={{ width: `${(task.position / task.total) * 100}%` }} />
      </div>

      <section className="flex flex-col gap-2 rounded-2xl border border-slate-200 bg-white p-5 text-center shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <p className="text-sm text-slate-500">
          {task.type === "recognition" ? cs.lesson.recognitionPrompt : cs.lesson.recallPrompt}
        </p>
        <p className="text-3xl font-bold break-words" lang={task.type === "recognition" ? language : "cs"}>
          {/* German stores the article (der/die/das); French/Italian store m/f. */}
          {task.type === "recognition" && language === "de" && task.gender ? `${task.gender} ` : ""}
          {task.prompt}
        </p>
        {task.gender && (task.type === "recall" || language !== "de") && (
          <p className="text-sm text-slate-500" lang={language}>
            ({task.gender})
          </p>
        )}
        {task.cloze && (
          <p className="text-lg text-slate-700 dark:text-slate-200" lang={language}>
            {task.cloze}
          </p>
        )}
        {task.example && (
          <p className="text-sm italic text-slate-500" lang={language}>
            {task.example}
          </p>
        )}
      </section>

      {task.type === "recognition" && task.options ? (
        <div className="grid gap-2">
          {task.options.map((o) => (
            <Button
              key={o.id}
              variant="secondary"
              className="w-full !justify-start !py-4 text-left"
              disabled={busy || finished}
              onClick={() => void send({ choice: o.id })}
            >
              {o.text}
            </Button>
          ))}
        </div>
      ) : (
        <form onSubmit={onSubmit} className="flex flex-col gap-2">
          <input
            ref={inputRef}
            value={text}
            onChange={(e) => setText(e.target.value)}
            disabled={busy || finished}
            placeholder={cs.lesson.answerPlaceholder}
            aria-label={cs.lesson.answerPlaceholder}
            autoCapitalize="none"
            autoCorrect="off"
            autoComplete="off"
            spellCheck={false}
            lang={language}
            className="rounded-xl border border-slate-300 bg-white px-4 py-4 text-center text-xl outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-500/30 dark:border-slate-700 dark:bg-slate-900"
          />
          {task.hint && <p className="text-center text-sm text-slate-500">{task.hint}</p>}
          {!finished && (
            <div className="flex flex-wrap justify-center gap-1">
              {SPECIAL_CHARS[language].map((c) => (
                <button
                  key={c}
                  type="button"
                  className="min-w-9 rounded-lg bg-slate-100 px-2 py-1.5 font-medium dark:bg-slate-800"
                  onClick={() => {
                    setText((t) => t + c);
                    inputRef.current?.focus();
                  }}
                >
                  {c}
                </button>
              ))}
            </div>
          )}
          {!finished && (
            <Button type="submit" disabled={busy || !text.trim()}>
              {cs.lesson.check}
            </Button>
          )}
        </form>
      )}

      {result && <Feedback result={result} />}
      {netError && <Notice tone="error">{cs.common.offline}</Notice>}

      {finished ? (
        <Button onClick={() => void advance(session)} autoFocus>
          {cs.lesson.next}
        </Button>
      ) : (
        <div className="flex gap-2">
          <Button
            variant="ghost"
            className="flex-1"
            disabled={busy || (task.type === "recognition" ? task.hint_level >= 1 : task.hint_level >= 2)}
            onClick={() => void hint()}
          >
            <Lightbulb className="size-4" aria-hidden /> {cs.lesson.hint}
          </Button>
          <Button variant="ghost" className="flex-1" disabled={busy} onClick={() => void send("reveal")}>
            <Eye className="size-4" aria-hidden /> {cs.lesson.reveal}
          </Button>
        </div>
      )}
    </div>
  );
}
