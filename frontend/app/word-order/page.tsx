"use client";

import { ArrowDownUp, Undo2 } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { AppShell, FullPageStatus, LanguagePicker } from "@/components/AppShell";
import { Kbd } from "@/components/Kbd";
import { TapText } from "@/components/TapText";
import { Button, Notice } from "@/components/ui";
import { checkWordOrder, nextWordOrder, type Language, type WordOrderPuzzle } from "@/lib/api";
import { useAuth, useRequireMe } from "@/lib/auth";
import { cs } from "@/lib/i18n/cs";

const t = cs.wordOrder;
type Result = { correct: boolean; marks: boolean[]; sentence: string; cs: string | null };

function Trainer({ language, difficulty }: { language: Language; difficulty: "auto" | "easy" | "medium" | "hard" }) {
  const [puzzle, setPuzzle] = useState<WordOrderPuzzle | null>(null);
  const [empty, setEmpty] = useState(false);
  const [failed, setFailed] = useState(false);
  const [placed, setPlaced] = useState<number[]>([]); // indices into puzzle.tiles
  const [typed, setTyped] = useState("");
  const [result, setResult] = useState<Result | null>(null);
  const [busy, setBusy] = useState(false);
  const done = useRef<string[]>([]);

  const load = useCallback(async () => {
    setResult(null);
    setPlaced([]);
    setTyped("");
    try {
      const p = await nextWordOrder(language, done.current.slice(-30));
      if (p.ref === null) setEmpty(true);
      else setPuzzle(p);
      setFailed(false);
    } catch {
      setFailed(true);
    }
  }, [language]);

  useEffect(() => {
    void load();
  }, [load]);

  const free = puzzle ? puzzle.tiles.map((_, i) => i).filter((i) => !placed.includes(i)) : [];
  const hard = difficulty === "hard";
  const complete = !!puzzle && (hard ? typed.trim().split(/\s+/).length === puzzle.tiles.length : placed.length === puzzle.tiles.length);

  const check = useCallback(async () => {
    if (!puzzle || busy) return;
    setBusy(true);
    try {
      setResult(await checkWordOrder(language, puzzle.ref, hard ? typed.trim().split(/\s+/) : placed.map((i) => puzzle.tiles[i]!)));
      done.current.push(puzzle.ref);
    } catch {
      setFailed(true);
    } finally {
      setBusy(false);
    }
  }, [puzzle, busy, language, placed, hard, typed]);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.ctrlKey || e.metaKey || e.altKey || !puzzle) return;
      if ((e.target as HTMLElement | null)?.closest("input, textarea")) return;
      if (result) {
        if (e.key === "Enter") {
          e.preventDefault();
          void load();
        }
        return;
      }
      const n = Number(e.key);
      if (n >= 1 && n <= free.length) {
        e.preventDefault();
        setPlaced((p) => [...p, free[n - 1]!]);
      } else if (e.key === "Backspace") {
        e.preventDefault();
        setPlaced((p) => p.slice(0, -1));
      } else if (e.key === "Enter" && complete) {
        e.preventDefault();
        void check();
      }
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [puzzle, result, free, complete, check, load]);

  if (empty) return <Notice>{t.empty}</Notice>;
  if (failed && !puzzle) return <Notice tone="error">{cs.common.error}</Notice>;
  if (!puzzle) return <p className="text-sm text-slate-500">{cs.common.loading}</p>;

  return (
    <section className="flex flex-col gap-4 rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
      {puzzle.cs ? (
        <p className="text-lg">
          <span className="text-sm text-slate-500">{t.meaning}</span> {puzzle.cs}
        </p>
      ) : (
        puzzle.hint && (
          <p className="text-sm text-slate-600 dark:text-slate-300">
            {t.hint} <strong lang={language}>{puzzle.hint}</strong>
          </p>
        )
      )}

      {hard ? (
        <label className="flex flex-col gap-2 text-sm font-medium">
          {t.hardPrompt}
          <input value={typed} onChange={(event) => setTyped(event.target.value)} disabled={busy || !!result} lang={language} className="rounded-xl border border-slate-300 bg-white px-3 py-3 text-lg dark:border-slate-700 dark:bg-slate-950" />
        </label>
      ) : <>
      <div
        className={`flex min-h-16 flex-wrap items-center gap-2 rounded-xl border-2 border-dashed p-3 ${
          result ? (result.correct ? "border-emerald-400" : "border-rose-300") : "border-slate-300 dark:border-slate-700"
        }`}
        lang={language}
        aria-label={t.pick}
      >
        {placed.length === 0 && <span className="text-sm text-slate-400">{t.pick}</span>}
        {placed.map((ti, pos) => {
          const mark = result?.marks[pos];
          return (
            <button
              key={`${ti}-${pos}`}
              type="button"
              disabled={!!result}
              onClick={() => setPlaced((p) => p.filter((x) => x !== ti))}
              className={`rounded-lg px-3 py-2 text-lg font-medium motion-safe:animate-pop-in ${
                mark === undefined
                  ? "bg-brand-500 text-white"
                  : mark
                    ? "bg-emerald-100 text-emerald-900 dark:bg-emerald-900/50 dark:text-emerald-100"
                    : "bg-rose-100 text-rose-900 line-through decoration-rose-400 dark:bg-rose-900/50 dark:text-rose-100"
              }`}
            >
              {puzzle.tiles[ti]}
            </button>
          );
        })}
        {complete && <span className="text-lg font-semibold">{puzzle.end}</span>}
      </div>

      {!result && (
        <div className="flex flex-wrap gap-2" lang={language}>
          {free.map((ti, k) => (
            <button
              key={ti}
              type="button"
              onClick={() => setPlaced((p) => [...p, ti])}
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-2 text-lg font-medium shadow-sm hover:border-brand-500 hover:bg-brand-500/5 dark:border-slate-700 dark:bg-slate-950"
            >
              <Kbd>{String(k + 1)}</Kbd>
              {puzzle.tiles[ti]}
            </button>
          ))}
        </div>
      )}
      </>}

      {result && (
        <div aria-live="polite" className="flex flex-col gap-1">
          <p className={`font-semibold ${result.correct ? "text-emerald-700 dark:text-emerald-300" : "text-rose-700 dark:text-rose-300"}`}>
            {result.correct ? t.right : t.wrong}
          </p>
          <p className="text-xl" lang={language}>
            <TapText text={result.sentence} language={language} />
          </p>
          {!result.correct && <p className="text-xs text-slate-500">{t.otherOrder}</p>}
        </div>
      )}
      {failed && <Notice tone="error">{cs.common.error}</Notice>}

      <div className="flex flex-wrap items-center justify-between gap-2">
        <Button variant="ghost" disabled={!!result || hard || placed.length === 0} onClick={() => setPlaced((p) => p.slice(0, -1))}>
          <Undo2 className="size-4" aria-hidden /> {t.undo}
        </Button>
        {result ? (
          <Button onClick={() => void load()}>{t.next}</Button>
        ) : (
          <Button disabled={!complete || busy} onClick={() => void check()}>
            {t.check}
          </Button>
        )}
      </div>
      {!hard && <p className="hidden text-xs text-slate-400 lg:block">{t.keys}</p>}
    </section>
  );
}

export default function WordOrderPage() {
  const me = useRequireMe();
  const { state } = useAuth();
  if (state.kind === "error") return <FullPageStatus text={cs.common.offline} />;
  if (!me) return <FullPageStatus text={cs.common.loading} />;
  const language = me.acting.active_language;
  return (
    <AppShell me={me}>
      <div className="flex flex-col gap-2">
        <h1 className="flex items-center gap-2 text-2xl font-bold">
          <ArrowDownUp className="size-6 text-brand-500" aria-hidden /> {t.title}
        </h1>
        <p className="max-w-3xl text-slate-600 dark:text-slate-300">{t.intro}</p>
        <LanguagePicker me={me} />
      </div>
      <Trainer key={language} language={language} difficulty={me.acting.settings.practice_difficulty} />
    </AppShell>
  );
}
