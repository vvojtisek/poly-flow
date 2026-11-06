"use client";

import { ListChecks, Shapes } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { AppShell, FullPageStatus, LanguagePicker } from "@/components/AppShell";
import { Kbd } from "@/components/Kbd";
import { Panel } from "@/components/Panel";
import { Button, Notice } from "@/components/ui";
import { ApiError, getGenders, type GenderNoun, type GenderSet, type Language } from "@/lib/api";
import { useAuth, useRequireMe } from "@/lib/auth";
import { genderClass } from "@/lib/gender";
import { cs } from "@/lib/i18n/cs";

const t = cs.genders;
const ROUND_QUESTIONS = 10;
const RETRY_GAP = 3; // a missed noun comes back after this many others
const BIN_STYLE: Record<string, string> = {
  der: "border-sky-300 bg-sky-50 text-sky-800 dark:border-sky-800 dark:bg-sky-950 dark:text-sky-200",
  m: "border-sky-300 bg-sky-50 text-sky-800 dark:border-sky-800 dark:bg-sky-950 dark:text-sky-200",
  die: "border-rose-300 bg-rose-50 text-rose-800 dark:border-rose-800 dark:bg-rose-950 dark:text-rose-200",
  f: "border-rose-300 bg-rose-50 text-rose-800 dark:border-rose-800 dark:bg-rose-950 dark:text-rose-200",
  das: "border-emerald-300 bg-emerald-50 text-emerald-800 dark:border-emerald-800 dark:bg-emerald-950 dark:text-emerald-200",
};
const ARROWS: Record<string, number> = { ArrowLeft: 0, ArrowDown: 1, ArrowRight: 2 };

function shuffle<T>(xs: T[]): T[] {
  const a = [...xs];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j]!, a[i]!];
  }
  return a;
}

type Feedback = { noun: GenderNoun; picked: string; right: boolean };

function HintLine({ noun }: { noun: GenderNoun }) {
  const h = noun.hint;
  if (!h) return <p className="text-sm text-slate-500">{t.noRule}</p>;
  return (
    <p className="text-sm text-slate-700 dark:text-slate-200">
      {t.rule(h.suffix, t.short[h.gender] ?? h.gender, h.certainty === "always")}{" "}
      {h.exception && <strong className="text-amber-700 dark:text-amber-300">{t.exception}</strong>}
    </p>
  );
}

function Sorter({ data, mode, onRoundEnd }: { data: GenderSet; mode: "practice" | "round"; onRoundEnd: () => void }) {
  const [onlyMine, setOnlyMine] = useState(false);
  const metCount = useMemo(() => data.nouns.filter((n) => n.met).length, [data]);
  const pool = useMemo(() => (onlyMine ? data.nouns.filter((n) => n.met) : data.nouns), [data, onlyMine]);
  const [queue, setQueue] = useState<GenderNoun[]>(() => shuffle(pool));
  const [feedback, setFeedback] = useState<Feedback | null>(null);
  const [right, setRight] = useState(0);
  const [total, setTotal] = useState(0);
  const advanceTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const done = mode === "round" && total >= ROUND_QUESTIONS;
  const totalRef = useRef(total);
  totalRef.current = total;
  const report = useRef(onRoundEnd);
  report.current = onRoundEnd;

  useEffect(() => {
    setQueue(shuffle(pool));
    setFeedback(null);
  }, [pool]);

  useEffect(() => () => void (advanceTimer.current && clearTimeout(advanceTimer.current)), []);

  const noun = queue[0];

  const next = useCallback(
    (missed: GenderNoun | null) => {
      setFeedback(null);
      if (mode === "round" && totalRef.current >= ROUND_QUESTIONS) {
        report.current();
        return;
      }
      setQueue((q) => {
        const rest = q.slice(1);
        if (missed) rest.splice(Math.min(RETRY_GAP, rest.length), 0, missed);
        return rest.length ? rest : shuffle(pool);
      });
    },
    [pool, mode],
  );

  const pick = useCallback(
    (g: string) => {
      if (!noun || done) return;
      if (feedback) {
        // A second key press after a miss moves on.
        if (!feedback.right) next(feedback.noun);
        return;
      }
      const ok = g === noun.gender;
      setTotal((n) => n + 1);
      if (ok) setRight((n) => n + 1);
      setFeedback({ noun, picked: g, right: ok });
      if (ok) {
        advanceTimer.current = setTimeout(() => next(null), 450);
      }
    },
    [noun, feedback, next, mode, done],
  );

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const el = e.target as HTMLElement | null;
      if (e.ctrlKey || e.metaKey || e.altKey || e.repeat || el?.closest("input, select, textarea")) return;
      // Enter and Space on a focused button belong to that button.
      if ((e.key === "Enter" || e.key === " ") && el?.closest("button")) return;
      let i: number | undefined;
      if (/^[1-3]$/.test(e.key)) i = Number(e.key) - 1;
      else if (e.key in ARROWS) i = data.genders.length === 2 && e.key === "ArrowRight" ? 1 : ARROWS[e.key];
      else if ((e.key === "Enter" || e.key === " ") && feedback && !feedback.right) {
        e.preventDefault();
        next(feedback.noun);
        return;
      }
      if (i === undefined || i >= data.genders.length) return;
      e.preventDefault();
      pick(data.genders[i]!);
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [data.genders, pick, feedback, next]);

  if (!noun) return <Notice>{t.empty}</Notice>;

  return (
    <div className="flex flex-col gap-4">
      {mode === "round" ? (
        <div className="flex flex-col gap-1">
          <div className="h-2 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-800" role="progressbar" aria-valuemin={0} aria-valuemax={ROUND_QUESTIONS} aria-valuenow={Math.min(total, ROUND_QUESTIONS)}>
            <div className="h-full bg-brand-500 transition-[width]" style={{ width: `${(Math.min(total, ROUND_QUESTIONS) / ROUND_QUESTIONS) * 100}%` }} />
          </div>
          <p className="flex justify-between text-sm text-slate-500">
            <span>{t.roundProgress(Math.min(total, ROUND_QUESTIONS), ROUND_QUESTIONS)}</span>
            <span>{t.untimedRound}</span>
          </p>
        </div>
      ) : (
        <div className="flex flex-wrap items-center justify-between gap-2 text-sm text-slate-500">
          <span>{total > 0 && t.score(right, total)}</span>
          {metCount >= 10 && (
            <label className="flex items-center gap-2">
              <input type="checkbox" checked={onlyMine} onChange={(e) => setOnlyMine(e.target.checked)} />
              {t.onlyMine} ({metCount})
            </label>
          )}
        </div>
      )}

      <div
        key={`${noun.id}:${total}`}
        className={`flex min-h-40 flex-col items-center justify-center gap-1 rounded-3xl border-2 p-6 text-center motion-safe:animate-pop-in ${
          feedback ? (feedback.right ? "border-emerald-400 bg-emerald-50 dark:bg-emerald-950/40" : "border-rose-400 bg-rose-50 dark:bg-rose-950/40") : "border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900"
        }`}
      >
        <p lang={data.language} className="text-4xl font-bold lg:text-5xl">
          {feedback && data.language === "de" && <span className={`mr-3 ${genderClass(noun.gender)}`}>{noun.gender}</span>}
          <span className={feedback ? genderClass(noun.gender) : ""}>{noun.lemma}</span>
        </p>
        <p className="text-slate-500">{noun.translation}</p>
        {feedback && (
          <div className="mt-2 flex flex-col items-center gap-1" aria-live="polite">
            <p className={`font-semibold ${feedback.right ? "text-emerald-700 dark:text-emerald-300" : "text-rose-700 dark:text-rose-300"}`}>
              {feedback.right ? t.right : t.wrong(t.label[noun.gender] ?? noun.gender)}
            </p>
            {!feedback.right && <HintLine noun={noun} />}
            {!feedback.right && mode === "practice" && <p className="text-xs text-slate-500">{t.again}</p>}
          </div>
        )}
      </div>

      <div className={`grid gap-2 ${data.genders.length === 3 ? "grid-cols-3" : "grid-cols-2"}`}>
        {data.genders.map((g, i) => (
          <button
            key={g}
            type="button"
            disabled={done}
            onClick={() => pick(g)}
            className={`flex flex-col items-center gap-1 rounded-2xl border-2 py-4 text-xl font-bold transition-transform active:scale-95 disabled:opacity-40 ${BIN_STYLE[g] ?? ""} ${
              feedback && g === noun.gender ? "ring-4 ring-emerald-400" : ""
            } ${feedback && !feedback.right && g === feedback.picked ? "ring-4 ring-rose-400" : ""}`}
          >
            {t.label[g] ?? g}
            <span className="hidden text-xs font-normal opacity-70 lg:inline">
              <Kbd>{String(i + 1)}</Kbd>
            </span>
          </button>
        ))}
      </div>
      {feedback && !feedback.right && (
        <Button variant="secondary" onClick={() => next(feedback.noun)}>
          {cs.common.continue}
        </Button>
      )}
      <p className="hidden text-center text-xs text-slate-500 lg:block">{t.keys(data.genders.length)}</p>
    </div>
  );
}

function Rules({ data }: { data: GenderSet }) {
  return (
    <ul className="flex flex-col gap-1 text-sm">
      {data.rules.map((r) => (
        <li key={r.suffix} className="flex items-center justify-between gap-2 rounded-lg px-2 py-1 odd:bg-slate-50 dark:odd:bg-slate-800/50">
          <span lang={data.language} className="font-mono">
            -{r.suffix}
          </span>
          <span className={`font-semibold ${genderClass(r.gender)}`}>{t.short[r.gender] ?? r.gender}</span>
          <span className={`rounded-full px-2 text-xs ${r.certainty === "always" ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-200" : "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-200"}`}>
            {r.certainty === "always" ? t.always : t.usually}
          </span>
        </li>
      ))}
    </ul>
  );
}

function GenderTrainer({ language }: { language: Language }) {
  const [data, setData] = useState<GenderSet | null>(null);
  const [state, setState] = useState<"loading" | "none" | "error" | "ok">("loading");
  const [mode, setMode] = useState<"practice" | "round" | "round-done">("practice");
  const [run, setRun] = useState(0);

  useEffect(() => {
    let cancelled = false;
    getGenders(language)
      .then((d) => {
        if (cancelled) return;
        setData(d);
        setState("ok");
      })
      .catch((e) => !cancelled && setState(e instanceof ApiError && e.status === 404 ? "none" : "error"));
    return () => {
      cancelled = true;
    };
  }, [language]);

  if (state === "loading") return <p className="text-sm text-slate-500">{cs.common.loading}</p>;
  if (state === "none") return <Notice>{t.noGender}</Notice>;
  if (state === "error" || !data) return <Notice tone="error">{cs.common.error}</Notice>;
  if (!data.nouns.length) return <Notice>{t.empty}</Notice>;

  function endRound() {
    setMode("round-done");
  }

  return (
    <div className="grid gap-4 lg:grid-cols-3">
      <div className="flex flex-col gap-3 lg:col-span-2">
        <div role="tablist" className="flex gap-1">
          {(["practice", "round"] as const).map((m) => (
            <button
              key={m}
              type="button"
              role="tab"
              aria-selected={mode === m || (m === "round" && mode === "round-done")}
              onClick={() => setMode(m === "round" ? "round-done" : "practice")}
              className={`inline-flex items-center gap-1 rounded-lg px-3 py-1.5 text-sm font-semibold ${
                mode === m || (m === "round" && mode === "round-done") ? "bg-brand-500 text-white" : "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-200"
              }`}
            >
              {m === "round" && <ListChecks className="size-4" aria-hidden />}
              {m === "practice" ? t.practice : t.round}
            </button>
          ))}
        </div>
        {mode === "round-done" ? (
          <section className="flex flex-col items-center gap-3 rounded-3xl border border-slate-200 bg-white p-6 text-center dark:border-slate-800 dark:bg-slate-900">
            <p className="text-xl font-bold motion-safe:animate-pop-in">{t.roundDone}</p>
            <p className="text-sm text-slate-600 dark:text-slate-300">{t.untimedRound}</p>
            <Button
              onClick={() => {
                setRun((r) => r + 1);
                setMode("round");
              }}
            >
              <ListChecks className="size-5" aria-hidden />
              {t.startRound}
            </Button>
          </section>
        ) : (
          <Sorter key={`${mode}:${run}`} data={data} mode={mode} onRoundEnd={endRound} />
        )}
      </div>
      <Panel title={t.rules} icon={Shapes}>
        <Rules data={data} />
      </Panel>
    </div>
  );
}

export default function GendersPage() {
  const me = useRequireMe();
  const { state } = useAuth();
  if (state.kind === "error") return <FullPageStatus text={cs.common.offline} />;
  if (!me) return <FullPageStatus text={cs.common.loading} />;
  const language = me.acting.active_language;
  return (
    <AppShell me={me}>
      <section className="flex flex-col gap-4">
        <h1 className="flex items-center gap-2 text-2xl font-bold">
          <Shapes className="size-6 text-brand-500" aria-hidden />
          {t.title}
        </h1>
        <p className="max-w-2xl text-slate-600 dark:text-slate-300">{t.intro}</p>
        <LanguagePicker me={me} />
        <GenderTrainer key={`${me.acting.id}:${language}`} language={language} />
      </section>
    </AppShell>
  );
}
