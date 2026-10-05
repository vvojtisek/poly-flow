"use client";

import { Award, BookOpen, CheckCircle2, Eye, HelpCircle, Lightbulb, XCircle } from "lucide-react";
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
  type ExamLevel,
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

// A correct choice stays on screen this long (ms) before the next question replaces it.
const AUTO_ADVANCE_MS = 300;

type OptionState = "idle" | "pending" | "correct" | "wrong" | "muted";

// Each state keeps WCAG AA text contrast in both themes; correct and wrong also carry an icon,
// so the result never rests on colour alone.
const OPTION_BASE =
  "flex w-full items-center justify-between gap-3 rounded-xl border px-4 py-4 text-left text-base font-semibold outline-none motion-safe:transition-colors focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2 disabled:cursor-default dark:focus-visible:ring-offset-slate-950";
const OPTION_STATES: Record<OptionState, string> = {
  idle: "border-slate-300 bg-white text-slate-900 hover:border-brand-500 hover:bg-brand-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100 dark:hover:bg-slate-800",
  pending:
    "border-brand-500 bg-brand-50 text-slate-900 ring-2 ring-brand-500/40 dark:bg-slate-800 dark:text-slate-100",
  correct:
    "border-emerald-600 bg-emerald-50 text-emerald-950 dark:border-emerald-400 dark:bg-emerald-950 dark:text-emerald-50",
  wrong: "border-red-600 bg-red-50 text-red-950 dark:border-red-400 dark:bg-red-950 dark:text-red-50",
  muted: "border-slate-200 bg-white text-slate-600 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300",
};

type Phase =
  | { kind: "starting" }
  | { kind: "empty" }
  | { kind: "error"; retry: () => void }
  | { kind: "scene"; session: LessonSession }
  | { kind: "words"; session: LessonSession; index: number }
  | { kind: "task"; session: LessonSession; task: Task; result: AnswerResult | null }
  | { kind: "done"; session: LessonSession };

function Feedback({
  result,
  mode,
  audioUrl,
  announce = true,
}: {
  result: AnswerResult;
  mode: SessionMode;
  audioUrl?: string;
  announce?: boolean; // false: a persistent live region announces it instead (auto-advance)
}) {
  const good = result.correct;
  const note = result.note ? cs.feedback.notes[result.note] : null;
  if (result.verdict === "not_understood")
    return (
      <div role="status" className="flex flex-col gap-1 rounded-xl bg-slate-100 p-3 text-sm dark:bg-slate-800">
        <p className="font-semibold">{cs.feedback.not_understood}</p>
        <p>{cs.feedback.nothingHeard}</p>
        <p>{cs.feedback.speakAgain}</p>
      </div>
    );
  return (
    <div
      role={announce ? "status" : undefined}
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
      {mode === "placement" && !good && <p className="text-xs opacity-80">{cs.placement.missedNote}</p>}
      {mode === "exam" && !good && <p className="text-xs opacity-80">{cs.exam.missedNote}</p>}
    </div>
  );
}

/** How one answer option looks: the server's answer decides correct and wrong, not the client. */
function optionState(
  option: { id: number; text: string },
  chosen: number | null,
  result: AnswerResult | null,
  busy: boolean,
  finished: boolean,
): OptionState {
  // `expected` is the correct translation once it may be shown; options never repeat it.
  if (result?.expected != null && option.text === result.expected) return "correct";
  if (option.id === chosen) {
    if (busy) return "pending";
    if (result && result.verdict === "wrong") return "wrong";
  }
  return finished ? "muted" : "idle";
}

function PlacementDone({ session }: { session: LessonSession }) {
  const s = session.summary;
  if (!s.placed) return <Notice>{cs.placement.notPlaced}</Notice>;
  const level = s.level ?? 0;
  return (
    <div className="flex flex-col gap-3">
      <div className="rounded-2xl border border-slate-200 bg-white p-5 text-center shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <p className="text-xs text-slate-500">{cs.placement.levelTitle}</p>
        <p className="text-2xl font-bold">{cs.placement.level(level)}</p>
        {s.at_ceiling ? (
          <p className="mt-1 text-sm text-slate-500">{cs.placement.atCeiling(s.ceiling ?? level)}</p>
        ) : (
          level > 0 && (
            <p className="mt-1 text-sm text-slate-500">{cs.placement.range(s.level_low ?? 0, s.level_high ?? level)}</p>
          )
        )}
      </div>
      <dl className="grid grid-cols-2 gap-2 text-sm">
        {(
          [
            [cs.placement.summaryCorrect, `${s.first_try_correct ?? 0} / ${s.asked ?? 0}`],
            [cs.placement.summaryQueued, s.queued ?? 0],
          ] as const
        ).map(([label, value]) => (
          <div key={label} className="rounded-xl bg-slate-50 p-3 dark:bg-slate-800/60">
            <dt className="text-xs text-slate-500">{label}</dt>
            <dd className="text-xl font-bold tabular-nums">{value}</dd>
          </div>
        ))}
      </dl>
      <Notice>{cs.placement.nextSteps}</Notice>
    </div>
  );
}

function ExamDone({ session }: { session: LessonSession }) {
  const s = session.summary;
  const level = s.exam_level ?? "";
  const missed = s.missed ?? [];
  return (
    <div className="flex flex-col gap-3">
      <div
        className={`rounded-2xl border p-5 text-center shadow-sm ${
          s.passed
            ? "border-emerald-300 bg-emerald-50 dark:border-emerald-800 dark:bg-emerald-950"
            : "border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900"
        }`}
      >
        {s.passed && <Award className="mx-auto mb-1 size-8 text-emerald-600" aria-hidden />}
        <p className="text-xl font-bold">{s.passed ? cs.exam.passedTitle(level) : cs.exam.failedTitle}</p>
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
          {cs.exam.score(s.correct ?? 0, s.asked ?? 0, s.pass_correct ?? 0)}
        </p>
      </div>
      {!s.passed && s.retry_from && (
        <Notice>{cs.exam.retryFrom(new Date(s.retry_from).toLocaleDateString("cs-CZ"))}</Notice>
      )}
      {missed.length > 0 && (
        <section className="flex flex-col gap-2">
          <h3 className="font-semibold">{cs.exam.toPractise}</h3>
          <ul className="divide-y divide-slate-200 rounded-xl border border-slate-200 text-sm dark:divide-slate-800 dark:border-slate-800">
            {missed.map((w) => (
              <li key={`${w.lemma}:${w.translation}`} className="flex justify-between gap-2 px-3 py-2">
                <span className="font-medium" lang={session.language}>
                  {session.language === "de" && w.gender ? `${w.gender} ` : ""}
                  {w.lemma}
                </span>
                <span className="text-slate-500" lang="cs">
                  {w.translation}
                </span>
              </li>
            ))}
          </ul>
          <p className="text-xs text-slate-500">{cs.exam.practiseNote}</p>
        </section>
      )}
    </div>
  );
}

/**
 * learn: scene -> word cards -> practice (never graded). check: graded once, no hints.
 * placement: graded once like a check; the server picks each next question from the answers.
 * exam: graded once like a check, on a fixed sample of one level's band.
 */
export function LessonRunner({
  language,
  mode = "learn",
  level,
  onExit,
}: {
  language: Language;
  mode?: SessionMode;
  level?: ExamLevel; // exam only
  onExit?: () => void; // where "back" leads; the dashboard by default
}) {
  const router = useRouter();
  const [phase, setPhase] = useState<Phase>({ kind: "starting" });
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [netError, setNetError] = useState(false);
  const [chosen, setChosen] = useState<number | null>(null); // the option clicked on this task
  const [announcement, setAnnouncement] = useState("");
  // Reused until the server answers, so a retried request cannot double-count.
  const pendingKey = useRef<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const optionsRef = useRef<HTMLDivElement>(null);
  // The last choice came from the keyboard: disabled options drop focus, so it is put back.
  const refocusOptions = useRef(false);

  const advance = useCallback(async (session: LessonSession) => {
    try {
      const { task } = await nextTask(session.id);
      setText("");
      setChosen(null);
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
      const { session } = await startLesson(language, mode, level);
      if (!session) setPhase({ kind: "empty" });
      // A fresh lesson starts with its context; a resumed one continues the practice.
      else if (session.mode === "learn" && session.remaining === session.total && session.words.length) {
        setPhase(session.scene ? { kind: "scene", session } : { kind: "words", session, index: 0 });
      } else await advance(session);
    } catch {
      setPhase({ kind: "error", retry: () => void begin() });
    }
  }, [language, mode, level, advance]);

  useEffect(() => {
    void begin();
  }, [begin]);

  useEffect(() => {
    if (phase.kind === "task" && phase.task.type === "recall" && !phase.result?.task_done) {
      inputRef.current?.focus();
    }
    if (
      phase.kind === "task" &&
      phase.task.type === "recognition" &&
      !phase.result?.task_done &&
      refocusOptions.current
    ) {
      refocusOptions.current = false;
      optionsRef.current?.querySelector("button")?.focus();
    }
  }, [phase]);

  // One click answers a choice: a correct one shows green briefly, then the next question comes.
  // A wrong one (or a reveal) stays until the learner presses Další.
  const autoAdvance =
    phase.kind === "task" &&
    phase.task.type === "recognition" &&
    !!phase.result?.correct &&
    phase.result.task_done;
  useEffect(() => {
    if (phase.kind !== "task" || !autoAdvance) return;
    const { session, result } = phase;
    setAnnouncement(`${cs.feedback[result!.verdict]} ${cs.lesson.expected} ${result!.expected ?? ""}`);
    const timer = setTimeout(() => void advance(session), AUTO_ADVANCE_MS);
    return () => clearTimeout(timer);
  }, [phase, autoAdvance, advance]);

  const t =
    mode === "check" ? cs.check : mode === "placement" ? cs.placement : mode === "exam" ? cs.exam : cs.lesson;
  const exit = onExit ?? (() => router.push("/"));
  if (phase.kind === "starting") return <p className="text-center text-slate-500">{t.preparing}</p>;
  if (phase.kind === "empty")
    return (
      <div className="flex flex-col gap-4">
        <Notice>{t.empty}</Notice>
        <Button variant="secondary" onClick={exit}>
          {onExit && mode === "exam" ? cs.exam.back : cs.lesson.toDashboard}
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
  if (phase.kind === "done" && mode === "placement")
    return (
      <div className="flex flex-col gap-4">
        <h2 className="text-xl font-bold">{t.doneTitle}</h2>
        <PlacementDone session={phase.session} />
        <div className="flex flex-col gap-2 sm:flex-row">
          {(phase.session.summary.queued ?? 0) > 0 && (
            <Button className="flex-1" onClick={() => router.push("/check")}>
              {cs.placement.toCheck}
            </Button>
          )}
          <Button variant="secondary" className="flex-1" onClick={() => router.push("/")}>
            {cs.lesson.toDashboard}
          </Button>
        </div>
      </div>
    );
  if (phase.kind === "done" && mode === "exam")
    return (
      <div className="flex flex-col gap-4">
        <h2 className="text-xl font-bold">{t.doneTitle}</h2>
        <ExamDone session={phase.session} />
        <Button variant="secondary" onClick={exit}>
          {onExit ? cs.exam.back : cs.lesson.toDashboard}
        </Button>
      </div>
    );
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
    if (body !== "reveal" && body.choice !== undefined) {
      if (body.choice !== chosen) pendingKey.current = null; // a different option is a new attempt
      setChosen(body.choice);
    }
    setAnnouncement("");
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

  async function stop() {
    if (busy) return;
    setBusy(true);
    try {
      setPhase({ kind: "done", session: await completeLesson(session.id) });
    } catch {
      setNetError(true);
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
      <div className="flex items-center justify-between gap-2 text-xs text-slate-500 dark:text-slate-400">
        <span>
          {mode === "placement"
            ? cs.placement.question(task.position + 1, task.total)
            : cs.lesson.progress(task.position + 1, task.total)}
        </span>
        <SlowToggle />
        <span className="rounded-full bg-slate-100 px-2 py-0.5 text-slate-600 dark:bg-slate-800 dark:text-slate-300">
          {mode === "check"
            ? cs.check.title
            : mode === "exam"
              ? cs.exam.badgeName(level ?? "")
              : mode === "placement"
              ? cs.placement.title
              : task.is_new_item
                ? cs.lesson.newWord
                : cs.lesson.review}
        </span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-800">
        <div className="h-full bg-brand-500" style={{ width: `${(task.position / task.total) * 100}%` }} />
      </div>

      <section className="flex flex-col gap-2 rounded-2xl border border-slate-200 bg-white p-5 text-center shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <p className="text-sm text-slate-500 dark:text-slate-400">
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
            <p className="text-sm italic text-slate-500 dark:text-slate-400" lang={language}>
              {task.example}
            </p>
            <PlayButton url={taskAudioUrl(task.id, "example")} label={cs.audio.playSentence} size="sm" />
          </div>
        )}
      </section>

      {task.type === "recognition" && task.options ? (
        <div className="grid gap-2" ref={optionsRef}>
          {task.options.map((o) => {
            const state = optionState(o, chosen, result, busy, finished);
            return (
              <button
                key={`${task.id}:${o.id}`}
                type="button"
                data-state={state}
                className={`${OPTION_BASE} ${OPTION_STATES[state]}`}
                disabled={busy || finished}
                onClick={(e) => {
                  refocusOptions.current = e.detail === 0; // Enter or Space, not a pointer
                  void send({ choice: o.id });
                }}
              >
                <span>{o.text}</span>
                {state === "correct" && <CheckCircle2 className="size-5 shrink-0" aria-hidden />}
                {state === "wrong" && <XCircle className="size-5 shrink-0" aria-hidden />}
              </button>
            );
          })}
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
          announce={!autoAdvance}
        />
      )}
      {/* Outlives the question, so an auto-advanced result is still read out. */}
      <p className="sr-only" aria-live="polite">
        {announcement}
      </p>
      {netError && <Notice tone="error">{cs.common.offline}</Notice>}

      {autoAdvance ? null : finished ? (
        <Button onClick={() => void advance(session)} autoFocus>
          {cs.lesson.next}
        </Button>
      ) : mode !== "learn" ? (
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
      {mode === "placement" && (
        <Button variant="ghost" className="text-sm" disabled={busy} onClick={() => void stop()}>
          {cs.placement.stop}
        </Button>
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
