"use client";

import { AlarmClock } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { AppShell, FullPageStatus, LanguagePicker } from "@/components/AppShell";
import { ClockFace } from "@/components/ClockFace";
import { Kbd } from "@/components/Kbd";
import { PlayButton } from "@/components/PlayButton";
import { Button, Notice } from "@/components/ui";
import { clockAudioUrl, clockQuiz, type ClockTime, type Language } from "@/lib/api";
import { play } from "@/lib/audio";
import { useAuth, useRequireMe } from "@/lib/auth";
import { cs } from "@/lib/i18n/cs";
import { useHotkeys } from "@/lib/keyboard";

const t = cs.clock;
type Mode = "read" | "find";
type Level = "quarters" | "five";
type Quiz = { time: ClockTime; options: ClockTime[]; answer: number };

function tab(active: boolean) {
  return `rounded-xl px-3 py-2 text-sm font-semibold ${
    active ? "bg-brand-500 text-white" : "bg-slate-100 text-slate-700 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
  }`;
}

function optionClass(state: "idle" | "right" | "wrong" | "dim") {
  return {
    idle: "border-slate-300 hover:border-brand-500 hover:bg-brand-500/5 dark:border-slate-700",
    right: "border-emerald-500 bg-emerald-50 dark:bg-emerald-950/40",
    wrong: "border-rose-500 bg-rose-50 dark:bg-rose-950/40",
    dim: "border-slate-200 opacity-60 dark:border-slate-800",
  }[state];
}

function Trainer({ language }: { language: Language }) {
  const [mode, setMode] = useState<Mode>("read");
  const [level, setLevel] = useState<Level>("quarters");
  const [quiz, setQuiz] = useState<Quiz | null>(null);
  const [picked, setPicked] = useState<number | null>(null);
  const [streak, setStreak] = useState(0);
  const [failed, setFailed] = useState(false);
  useHotkeys();

  const load = useCallback(async (lv: Level) => {
    setPicked(null);
    try {
      setQuiz(await clockQuiz(language, lv));
      setFailed(false);
    } catch {
      setFailed(true);
    }
  }, [language]);

  useEffect(() => {
    void load(level);
  }, [load, level]);

  useEffect(() => {
    if (quiz && mode === "find") void play(clockAudioUrl(quiz.time, language));
  }, [quiz, mode, language]);

  function pick(i: number) {
    if (!quiz || picked !== null) return;
    setPicked(i);
    const right = i === quiz.answer;
    setStreak((s) => (right ? s + 1 : 0));
    if (mode === "read") void play(clockAudioUrl(quiz.time, language));
  }

  if (failed && !quiz) return <Notice tone="error">{cs.common.error}</Notice>;
  if (!quiz) return <p className="text-sm text-slate-500">{cs.common.loading}</p>;
  const state = (i: number) => (picked === null ? "idle" : i === quiz.answer ? "right" : i === picked ? "wrong" : "dim");
  const url = clockAudioUrl(quiz.time, language);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap gap-2">
        {(["read", "find"] as Mode[]).map((m) => (
          <button key={m} type="button" aria-pressed={mode === m} className={tab(mode === m)} onClick={() => { setMode(m); void load(level); }}>
            {t.modes[m]}
          </button>
        ))}
        <span className="mx-1 w-px self-stretch bg-slate-200 dark:bg-slate-700" aria-hidden />
        {(["quarters", "five"] as Level[]).map((lv) => (
          <button key={lv} type="button" aria-pressed={level === lv} className={tab(level === lv)} onClick={() => setLevel(lv)}>
            {t.level[lv]}
          </button>
        ))}
      </div>

      <section className="flex flex-col gap-4 rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
        <p className="text-sm text-slate-500">{mode === "read" ? t.readHelp : t.findHelp}</p>
        {mode === "read" ? (
          <>
            <div className="grid place-items-center">
              <ClockFace hour={quiz.time.hour} minute={quiz.time.minute} size={200} label={t.clockLabel(quiz.time.digits)} />
            </div>
            <div className="grid gap-2 sm:grid-cols-2" lang={language}>
              {quiz.options.map((o, i) => (
                <button
                  key={i}
                  type="button"
                  data-hotkey={String(i + 1)}
                  disabled={picked !== null}
                  onClick={() => pick(i)}
                  className={`flex items-center gap-2 rounded-xl border-2 px-4 py-3 text-left text-lg font-medium ${optionClass(state(i))}`}
                >
                  <Kbd>{String(i + 1)}</Kbd>
                  {o.phrase}
                </button>
              ))}
            </div>
          </>
        ) : (
          <>
            <p className="flex items-center justify-center gap-3 text-center text-2xl font-semibold" lang={language}>
              {quiz.time.phrase}
              <PlayButton url={url} size="sm" />
            </p>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              {quiz.options.map((o, i) => (
                <button
                  key={i}
                  type="button"
                  data-hotkey={String(i + 1)}
                  disabled={picked !== null}
                  onClick={() => pick(i)}
                  aria-label={t.clockOption(i + 1)}
                  className={`flex flex-col items-center gap-1 rounded-2xl border-2 p-2 ${optionClass(state(i))}`}
                >
                  <ClockFace hour={o.hour} minute={o.minute} size={120} label={t.clockOption(i + 1)} />
                  <Kbd>{String(i + 1)}</Kbd>
                </button>
              ))}
            </div>
          </>
        )}

        {picked !== null && (
          <div aria-live="polite" className="flex flex-col gap-1 rounded-xl bg-slate-50 p-3 dark:bg-slate-800/60">
            <p className={`font-semibold ${picked === quiz.answer ? "text-emerald-700 dark:text-emerald-300" : "text-rose-700 dark:text-rose-300"}`}>
              {picked === quiz.answer ? t.right : t.wrong}
            </p>
            <p className="flex flex-wrap items-center gap-2 text-lg">
              <span className="font-bold tabular-nums">{quiz.time.digits}</span>=<span lang={language}>{quiz.time.phrase}</span>
              {mode === "read" && <PlayButton url={url} size="sm" />}
            </p>
            {quiz.time.czech !== quiz.time.digits && (
              <p className="text-sm text-slate-600 dark:text-slate-300">
                {t.czech} {quiz.time.czech}
              </p>
            )}
          </div>
        )}
        <div className="flex items-center justify-between gap-2">
          <span className="text-sm text-slate-500">{streak > 1 ? t.streak(streak) : ""}</span>
          <Button data-hotkey="enter" disabled={picked === null} onClick={() => void load(level)}>
            {t.next}
          </Button>
        </div>
      </section>
      <p className="max-w-3xl text-sm text-slate-600 dark:text-slate-300">{t.hint[language]}</p>
    </div>
  );
}

export default function ClockPage() {
  const me = useRequireMe();
  const { state } = useAuth();
  if (state.kind === "error") return <FullPageStatus text={cs.common.offline} />;
  if (!me) return <FullPageStatus text={cs.common.loading} />;
  const language = me.acting.active_language;
  return (
    <AppShell me={me}>
      <div className="flex flex-col gap-2">
        <h1 className="flex items-center gap-2 text-2xl font-bold">
          <AlarmClock className="size-6 text-brand-500" aria-hidden /> {t.title}
        </h1>
        <p className="max-w-3xl text-slate-600 dark:text-slate-300">{t.intro}</p>
        <LanguagePicker me={me} />
      </div>
      <Trainer key={language} language={language} />
    </AppShell>
  );
}
