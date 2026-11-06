"use client";

import { Hash } from "lucide-react";
import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";

import { AnswerInput } from "@/components/AnswerInput";
import { AppShell, FullPageStatus, LanguagePicker } from "@/components/AppShell";
import { PlayButton, SlowToggle } from "@/components/PlayButton";
import { Button, Notice } from "@/components/ui";
import { checkNumber, numberAudioUrl, spellNumber, type Language } from "@/lib/api";
import { play, useClipState } from "@/lib/audio";
import { useAuth, useRequireMe } from "@/lib/auth";
import { cs } from "@/lib/i18n/cs";

const t = cs.numbers;
type Mode = "write" | "listen" | "read";
type Range = "small" | "tens" | "hundreds" | "big";
const MODES: Mode[] = ["write", "listen", "read"];
const RANGES: Record<Range, [number, number]> = { small: [0, 20], tens: [0, 100], hundreds: [100, 999], big: [1000, 9999] };

function pick([lo, hi]: [number, number], not?: number) {
  for (;;) {
    const n = lo + Math.floor(Math.random() * (hi - lo + 1));
    if (n !== not || hi === lo) return n;
  }
}

function tab(active: boolean) {
  return `rounded-xl px-3 py-2 text-sm font-semibold ${
    active ? "bg-brand-500 text-white" : "bg-slate-100 text-slate-700 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
  }`;
}

function Trainer({ language }: { language: Language }) {
  const [mode, setMode] = useState<Mode>("write");
  const [range, setRange] = useState<Range>("tens");
  const [n, setN] = useState(() => pick(RANGES.tens));
  const [words, setWords] = useState<string | null>(null);
  const [text, setText] = useState("");
  const [result, setResult] = useState<{ correct: boolean; words: string } | null>(null);
  const [streak, setStreak] = useState(0);
  const [failed, setFailed] = useState(false);
  const [busy, setBusy] = useState(false);
  const input = useRef<HTMLInputElement>(null);
  const url = numberAudioUrl(n, language);
  const audio = useClipState(url);

  const fresh = useCallback(
    (r: Range = range) => {
      setN((prev) => pick(RANGES[r], prev));
      setText("");
      setResult(null);
      requestAnimationFrame(() => input.current?.focus());
    },
    [range],
  );

  // The words for "read", and the audio for "listen", whenever the number changes.
  useEffect(() => {
    setWords(null);
    if (mode === "read") {
      let cancelled = false;
      spellNumber(n, language)
        .then((r) => !cancelled && setWords(r.words))
        .catch(() => !cancelled && setFailed(true));
      return () => {
        cancelled = true;
      };
    }
    if (mode === "listen") void play(url);
  }, [n, mode, language, url]);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (result) return fresh();
    if (!text.trim() || busy) return;
    setBusy(true);
    try {
      const r = await checkNumber({ language, n, answer: text, direction: mode === "write" ? "write" : "read" });
      setResult(r);
      setStreak((s) => (r.correct ? s + 1 : 0));
      setFailed(false);
      if (mode === "write" && r.correct) void play(url);
    } catch {
      setFailed(true);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap gap-2" role="radiogroup" aria-label={t.title}>
        {MODES.map((m) => (
          <button key={m} type="button" role="radio" aria-checked={mode === m} className={tab(mode === m)} onClick={() => { setMode(m); fresh(); }}>
            {t.modes[m]}
          </button>
        ))}
      </div>
      <div className="flex flex-wrap items-center gap-2" role="radiogroup" aria-label={t.range}>
        <span className="text-sm text-slate-500">{t.range}:</span>
        {(Object.keys(RANGES) as Range[]).map((r) => (
          <button key={r} type="button" role="radio" aria-checked={range === r} className={tab(range === r)} onClick={() => { setRange(r); fresh(r); }}>
            {t.ranges[r]}
          </button>
        ))}
      </div>

      <form onSubmit={submit} className="flex flex-col gap-3 rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
        <p className="text-sm text-slate-500">{t.modeHelp[mode]}</p>
        <div className="grid min-h-24 place-items-center">
          {mode === "write" && <p className="text-6xl font-bold tabular-nums">{n.toLocaleString("cs-CZ")}</p>}
          {mode === "read" && (
            <p lang={language} className="text-center text-2xl font-semibold">
              {words ?? cs.common.loading}
            </p>
          )}
          {mode === "listen" && (
            <div className="flex items-center gap-3">
              <PlayButton url={url} label={t.listenAgain} hotkey />
              <SlowToggle />
            </div>
          )}
        </div>
        {mode === "listen" && audio === "error" && <Notice>{t.noAudio}</Notice>}
        {mode === "write" ? (
          <AnswerInput ref={input} language={language} value={text} onChange={setText} disabled={!!result} placeholder={t.placeholderWords} />
        ) : (
          <input
            ref={input}
            inputMode="numeric"
            autoComplete="off"
            value={text}
            onChange={(e) => setText(e.target.value)}
            disabled={!!result}
            placeholder={t.placeholderDigits}
            aria-label={t.placeholderDigits}
            className="rounded-xl border border-slate-300 bg-white px-4 py-3 text-2xl tabular-nums outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-500/30 dark:border-slate-700 dark:bg-slate-950"
          />
        )}
        {result && (
          <div aria-live="polite" className={`rounded-xl p-3 ${result.correct ? "bg-emerald-50 dark:bg-emerald-950/40" : "bg-rose-50 dark:bg-rose-950/40"}`}>
            <p className={`font-semibold ${result.correct ? "text-emerald-700 dark:text-emerald-300" : "text-rose-700 dark:text-rose-300"}`}>
              {result.correct ? t.right : t.wrong}
            </p>
            <p className="flex flex-wrap items-center gap-2 text-lg">
              <span className="font-bold tabular-nums">{n.toLocaleString("cs-CZ")}</span>=
              <span lang={language}>{result.words}</span>
              <PlayButton url={url} size="sm" />
            </p>
          </div>
        )}
        {failed && <Notice tone="error">{cs.common.error}</Notice>}
        <div className="flex items-center justify-between gap-3">
          <span className="text-sm text-slate-500" aria-live="polite">
            {streak > 1 ? t.streak(streak) : ""}
          </span>
          <Button type="submit" disabled={busy || (!result && !text.trim())}>
            {result ? t.next : t.check}
          </Button>
        </div>
      </form>
      <p className="max-w-3xl text-sm text-slate-600 dark:text-slate-300">{t.hint[language]}</p>
    </div>
  );
}

export default function NumbersPage() {
  const me = useRequireMe();
  const { state } = useAuth();
  if (state.kind === "error") return <FullPageStatus text={cs.common.offline} />;
  if (!me) return <FullPageStatus text={cs.common.loading} />;
  const language = me.acting.active_language;
  return (
    <AppShell me={me}>
      <div className="flex flex-col gap-2">
        <h1 className="flex items-center gap-2 text-2xl font-bold">
          <Hash className="size-6 text-brand-500" aria-hidden /> {t.title}
        </h1>
        <p className="max-w-3xl text-slate-600 dark:text-slate-300">{t.intro}</p>
        <LanguagePicker me={me} />
      </div>
      <Trainer key={language} language={language} />
    </AppShell>
  );
}
