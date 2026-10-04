"use client";

import { BookOpen, CheckCircle2, Eye, HelpCircle, Lightbulb, XCircle } from "lucide-react";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";

import { PlayButton, SlowToggle } from "@/components/PlayButton";
import { SceneView } from "@/components/SceneView";
import { SpeakAnswer } from "@/components/SpeakAnswer";
import { Button, Notice } from "@/components/ui";
import {
  completeLesson,
  newIdempotencyKey,
  nextTask,
  requestHint,
  revealAnswer,
  startLesson,
  submitAnswer,
  taskAudioUrl,
  wordAudioUrl,
  type AnswerResult,
  type Language,
  type LessonSession,
  type SessionMode,
  type Task,
} from "@/lib/api";
import { cs } from "@/lib/i18n/cs";

const SPECIAL_CHARS: Record<Language, string[]> = {
  de: ["ä", "ö", "ü", "ß", "Ä", "Ö", "Ü"],
  fr: ["é", "è", "ê", "à", "â", "ç", "ô", "î", "û", "ù", "ë", "œ"],
  it: ["à", "è", "é", "ì", "ò", "ù"],
  en: [],
};

type Phase =
  | { kind: "starting" }
  | { kind: "empty" }
  | { kind: "error"; retry: () => void }
  | { kind: "scene"; session: LessonSession }
  | { kind: "words"; session: LessonSession; index: number }
  | { kind: "task"; session: LessonSession; task: Task; result: AnswerResult | null }
  | { kind: "done"; session: LessonSession };

function Feedback({ result, mode, audioUrl }: { result: AnswerResult; mode: SessionMode; audioUrl?: string }) {
  const good = result.correct;
  const note = result.note ? cs.feedback.notes[result.note] : null;
  if (result.verdict === "not_understood")
    return (
      <div role="status" className="flex flex-col gap-1 rounded-xl bg-slate-100 p-3 text-sm dark:bg-slate-800">
        <p className="font-semibold">{cs.feedback.not_understood}</p>
        <p>{result.heard ? cs.feedback.heard(result.heard) : cs.feedback.nothingHeard}</p>
        <p>{cs.feedback.speakAgain}</p>
      </div>
    );
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
        <p className="flex flex-wrap items-center gap-x-1">
          {cs.lesson.expected} <strong>{result.expected}</strong>
          {audioUrl && result.task_done && <PlayButton url={audioUrl} label={cs.audio.playWord} size="sm" />}
          {result.meaning && result.meaning !== result.expected && (
            <>
              {" "}
              · {cs.lesson.meaning} {result.meaning}
            </>
          )}
        </p>
      )}
      {mode === "learn" && !result.task_done && <p>{cs.lesson.wrongTryAgain}</p>}
      {mode === "check" && !good && <p className="text-xs opacity-80">{cs.check.missedNote}</p>}
    </div>
  );
}

/** learn: scene -> word cards -> practice (never graded). check: graded once, no hints. */
export function LessonRunner({ language, mode = "learn" }: { language: Language; mode?: SessionMode }) {
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
      const { session } = await startLesson(language, mode);
      if (!session) setPhase({ kind: "empty" });
      // A fresh lesson starts with its context; a resumed one continues the practice.
      else if (session.mode === "learn" && session.remaining === session.total && session.words.length) {
        setPhase(session.scene ? { kind: "scene", session } : { kind: "words", session, index: 0 });
      } else await advance(session);
    } catch {
      setPhase({ kind: "error", retry: () => void begin() });
    }
  }, [language, mode, advance]);

  useEffect(() => {
    void begin();
  }, [begin]);

  useEffect(() => {
    if (phase.kind === "task" && phase.task.type === "recall" && !phase.result?.task_done) {
      inputRef.current?.focus();
    }
  }, [phase]);

  const t = mode === "check" ? cs.check : cs.lesson;
  if (phase.kind === "starting") return <p className="text-center text-slate-500">{t.preparing}</p>;
  if (phase.kind === "empty")
    return (
      <div className="flex flex-col gap-4">
        <Notice>{t.empty}</Notice>
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
  if (phase.kind === "scene") {
    const { session } = phase;
    return (
      <div className="flex flex-col gap-4">
        <p className="text-sm text-slate-500">
          {cs.lesson.sceneHelp} {cs.lesson.learnHelp}
        </p>
        <div className="flex justify-end">
          <SlowToggle />
        </div>
        <SceneView scene={session.scene!} language={language} sessionId={session.id} />
        <Button onClick={() => setPhase({ kind: "words", session, index: 0 })} autoFocus>
          {cs.lesson.toWords}
        </Button>
      </div>
    );
  }
  if (phase.kind === "words") {
    const { session, index } = phase;
    const w = session.words[index]!;
    const last = index === session.words.length - 1;
    return (
      <div className="flex flex-col gap-4">
        <div className="flex items-center justify-between gap-2 text-xs text-slate-500">
          <span>{cs.lesson.wordsTitle}</span>
          <span className="flex items-center gap-2">
            <SlowToggle />
            {cs.lesson.wordOf(index + 1, session.words.length)}
          </span>
        </div>
        <section className="flex flex-col gap-2 rounded-2xl border border-slate-200 bg-white p-5 text-center shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <div className="flex items-center justify-center gap-1">
            <p className="text-3xl font-bold break-words" lang={language}>
              {language === "de" && w.gender ? `${w.gender} ` : ""}
              {w.lemma}
            </p>
            <PlayButton url={wordAudioUrl(session.id, w.id, "word")} label={cs.audio.playWord} />
          </div>
          {w.gender && language !== "de" && (
            <p className="text-sm text-slate-500" lang={language}>
              ({w.gender})
            </p>
          )}
          {w.ipa && <p className="text-sm text-slate-500">/{w.ipa}/</p>}
          <p className="text-xl text-slate-700 dark:text-slate-200" lang="cs">
            {w.translation}
          </p>
          {w.context && (
            <div className="mt-2 rounded-xl bg-slate-50 p-3 text-left dark:bg-slate-800/60">
              <div className="flex items-start gap-1">
                <p className="flex-1 italic" lang={language}>
                  {w.context}
                </p>
                <PlayButton url={wordAudioUrl(session.id, w.id, "context")} label={cs.audio.playSentence} size="sm" />
              </div>
              {w.context_cs && (
                <p className="text-sm text-slate-500" lang="cs">
                  {w.context_cs}
                </p>
              )}
            </div>
          )}
        </section>
        <div className="flex gap-2">
          {index > 0 && (
            <Button variant="secondary" className="flex-1" onClick={() => setPhase({ ...phase, index: index - 1 })}>
              {cs.lesson.back}
            </Button>
          )}
          <Button
            className="flex-1"
            autoFocus
            onClick={() => (last ? void advance(session) : setPhase({ ...phase, index: index + 1 }))}
          >
            {last ? cs.lesson.toPractice : cs.lesson.next}
          </Button>
        </div>
      </div>
    );
  }
  if (phase.kind === "done") {
    const s = phase.session.summary;
    const tiles: (readonly [string, string | number])[] =
      mode === "check"
        ? [
            [cs.check.summaryCorrect, `${s.first_try_correct ?? 0} / ${s.total ?? 0}`],
            [cs.check.summaryMissed, (s.total ?? 0) - (s.first_try_correct ?? 0)],
          ]
        : [
            [cs.lesson.summaryLearned, s.new_items ?? 0],
            [cs.lesson.summaryPracticed, s.total ?? 0],
          ];
    return (
      <div className="flex flex-col gap-4">
        <h2 className="text-xl font-bold">{t.doneTitle}</h2>
        <dl className="grid grid-cols-2 gap-2 text-sm">
          {tiles.map(([label, value]) => (
            <div key={label} className="rounded-xl bg-slate-50 p-3 dark:bg-slate-800/60">
              <dt className="text-xs text-slate-500">{label}</dt>
              <dd className="text-xl font-bold tabular-nums">{value}</dd>
            </div>
          ))}
        </dl>
        {mode === "learn" && <Notice>{cs.lesson.learnedNote}</Notice>}
        <div className="flex flex-col gap-2 sm:flex-row">
          <Button className="flex-1" onClick={() => void begin()}>
            {t.another}
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
      <div className="flex items-center justify-between gap-2 text-xs text-slate-500">
        <span>{cs.lesson.progress(task.position + 1, task.total)}</span>
        <SlowToggle />
        <span className="rounded-full bg-slate-100 px-2 py-0.5 dark:bg-slate-800">
          {mode === "check" ? cs.check.title : task.is_new_item ? cs.lesson.newWord : cs.lesson.review}
        </span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-800">
        <div className="h-full bg-brand-500" style={{ width: `${(task.position / task.total) * 100}%` }} />
      </div>

      <section className="flex flex-col gap-2 rounded-2xl border border-slate-200 bg-white p-5 text-center shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <p className="text-sm text-slate-500">
          {task.type === "recognition" ? cs.lesson.recognitionPrompt : cs.lesson.recallPrompt}
        </p>
        <div className="flex items-center justify-center gap-1">
          <p className="text-3xl font-bold break-words" lang={task.type === "recognition" ? language : "cs"}>
            {/* German stores the article (der/die/das); French/Italian store m/f. */}
            {task.type === "recognition" && language === "de" && task.gender ? `${task.gender} ` : ""}
            {task.prompt}
          </p>
          {/* A recall task asks for the word itself: its audio plays with the answer instead. */}
          {task.type === "recognition" && <PlayButton url={taskAudioUrl(task.id, "word")} label={cs.audio.playWord} />}
        </div>
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
          <div className="flex items-center justify-center gap-1">
            <p className="text-sm italic text-slate-500" lang={language}>
              {task.example}
            </p>
            <PlayButton url={taskAudioUrl(task.id, "example")} label={cs.audio.playSentence} size="sm" />
          </div>
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
          {!finished && SPECIAL_CHARS[language].length > 0 && (
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
          {!finished && (
            <SpeakAnswer
              key={task.id}
              taskId={task.id}
              disabled={busy}
              onResult={(r) => setPhase({ kind: "task", session, task, result: r })}
            />
          )}
        </form>
      )}

      {result && (
        <Feedback
          result={result}
          mode={mode}
          audioUrl={task.type === "recall" ? taskAudioUrl(task.id, "word") : undefined}
        />
      )}
      {netError && <Notice tone="error">{cs.common.offline}</Notice>}

      {finished ? (
        <Button onClick={() => void advance(session)} autoFocus>
          {cs.lesson.next}
        </Button>
      ) : mode === "check" ? (
        <Button variant="ghost" disabled={busy} onClick={() => void send("reveal")}>
          <HelpCircle className="size-4" aria-hidden /> {cs.check.dontKnow}
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
      {mode === "learn" && session.scene && (
        <details className="rounded-xl text-sm">
          <summary className="flex cursor-pointer items-center gap-2 text-slate-500">
            <BookOpen className="size-4" aria-hidden /> {cs.lesson.rereadScene}
          </summary>
          <div className="mt-2">
            <SceneView scene={session.scene} language={language} sessionId={session.id} />
          </div>
        </details>
      )}
    </div>
  );
}
