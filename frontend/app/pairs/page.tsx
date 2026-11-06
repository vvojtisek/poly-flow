"use client";

import { Ear, Volume2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { AppShell, FullPageStatus, LanguagePicker } from "@/components/AppShell";
import { Kbd } from "@/components/Kbd";
import { PlayButton, SlowToggle } from "@/components/PlayButton";
import { Button, Notice } from "@/components/ui";
import { getPairSets, pairAudioUrl, type Language, type PairSet } from "@/lib/api";
import { play, useClipState } from "@/lib/audio";
import { useAuth, useRequireMe } from "@/lib/auth";
import { cs } from "@/lib/i18n/cs";
import { useHotkeys } from "@/lib/keyboard";

const t = cs.pairs;
type Round = { pair: number; side: number };

function pickRound(set: PairSet, prev?: Round): Round {
  for (;;) {
    const r = { pair: Math.floor(Math.random() * set.pairs.length), side: Math.random() < 0.5 ? 0 : 1 };
    if (!prev || set.pairs.length < 2 || r.pair !== prev.pair) return r;
  }
}

function Quiz({ set, language }: { set: PairSet; language: Language }) {
  const [round, setRound] = useState<Round>(() => pickRound(set));
  const [picked, setPicked] = useState<number | null>(null);
  const [score, setScore] = useState({ right: 0, total: 0 });
  const url = pairAudioUrl(language, set.id, round.pair, round.side);
  const audio = useClipState(url);
  const [a, b] = set.pairs[round.pair]!;
  useHotkeys();

  useEffect(() => {
    void play(url);
  }, [url]);

  const next = useCallback(() => {
    setPicked(null);
    setRound((r) => pickRound(set, r));
  }, [set]);

  function choose(side: number) {
    if (picked !== null) return;
    setPicked(side);
    setScore((s) => ({ right: s.right + (side === round.side ? 1 : 0), total: s.total + 1 }));
  }

  return (
    <section className="flex flex-col gap-4 rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
      <p className="text-sm text-slate-600 dark:text-slate-300">{set.hint}</p>
      <div className="flex items-center justify-center gap-3">
        <button
          type="button"
          data-hotkey="play"
          onClick={() => void play(url)}
          aria-label={t.listen}
          className="grid size-20 place-items-center rounded-full bg-brand-500 text-white shadow-lg hover:bg-brand-600"
        >
          <Volume2 className="size-9" aria-hidden />
        </button>
        <SlowToggle />
      </div>
      {audio === "error" && <Notice>{t.noAudio}</Notice>}
      <p className="text-center text-sm font-medium text-slate-500">{t.which}</p>
      <div className="grid grid-cols-2 gap-3" lang={language}>
        {[a, b].map((w, side) => {
          const state = picked === null ? "" : side === round.side ? "right" : side === picked ? "wrong" : "dim";
          return (
            <button
              key={w.text}
              type="button"
              data-hotkey={String(side + 1)}
              disabled={picked !== null}
              onClick={() => choose(side)}
              className={`flex flex-col items-center gap-1 rounded-2xl border-2 px-3 py-4 ${
                state === "right"
                  ? "border-emerald-500 bg-emerald-50 dark:bg-emerald-950/40"
                  : state === "wrong"
                    ? "border-rose-500 bg-rose-50 dark:bg-rose-950/40"
                    : state === "dim"
                      ? "border-slate-200 opacity-60 dark:border-slate-800"
                      : "border-slate-300 hover:border-brand-500 hover:bg-brand-500/5 dark:border-slate-700"
              }`}
            >
              <span className="text-2xl font-bold">{w.text}</span>
              <span lang="cs" className="text-sm text-slate-500">
                {w.cs}
              </span>
              <Kbd>{String(side + 1)}</Kbd>
            </button>
          );
        })}
      </div>
      {picked !== null && (
        <div aria-live="polite" className="flex flex-col gap-2 rounded-xl bg-slate-50 p-3 dark:bg-slate-800/60">
          <p className={`font-semibold ${picked === round.side ? "text-emerald-700 dark:text-emerald-300" : "text-rose-700 dark:text-rose-300"}`}>
            {picked === round.side ? t.right : t.wrong}
          </p>
          <p className="flex flex-wrap items-center gap-3 text-sm" lang={language}>
            {t.compare}
            {[a, b].map((w, side) => (
              <span key={w.text} className="inline-flex items-center gap-1 font-semibold">
                {w.text} <PlayButton url={pairAudioUrl(language, set.id, round.pair, side)} size="sm" />
              </span>
            ))}
          </p>
        </div>
      )}
      <div className="flex items-center justify-between gap-2">
        <span className="text-sm text-slate-500">{score.total > 0 ? t.score(score.right, score.total) : ""}</span>
        <Button data-hotkey="enter" disabled={picked === null} onClick={next}>
          {t.next}
        </Button>
      </div>
    </section>
  );
}

function Trainer({ language }: { language: Language }) {
  const [sets, setSets] = useState<PairSet[] | null>(null);
  const [chosen, setChosen] = useState(0);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    getPairSets(language)
      .then((s) => !cancelled && setSets(s))
      .catch(() => !cancelled && setFailed(true));
    return () => {
      cancelled = true;
    };
  }, [language]);

  if (failed) return <Notice tone="error">{cs.common.error}</Notice>;
  if (!sets) return <p className="text-sm text-slate-500">{cs.common.loading}</p>;
  const set = sets[chosen];
  if (!set) return null;
  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap gap-2">
        {sets.map((s, i) => (
          <button
            key={s.id}
            type="button"
            aria-pressed={i === chosen}
            onClick={() => setChosen(i)}
            className={`rounded-xl px-3 py-2 text-sm font-semibold ${
              i === chosen ? "bg-brand-500 text-white" : "bg-slate-100 text-slate-700 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
            }`}
          >
            {s.title}
          </button>
        ))}
      </div>
      <Quiz key={set.id} set={set} language={language} />
      <p className="text-xs text-slate-500">{t.unreviewed}</p>
    </div>
  );
}

export default function PairsPage() {
  const me = useRequireMe();
  const { state } = useAuth();
  if (state.kind === "error") return <FullPageStatus text={cs.common.offline} />;
  if (!me) return <FullPageStatus text={cs.common.loading} />;
  const language = me.acting.active_language;
  return (
    <AppShell me={me}>
      <div className="flex flex-col gap-2">
        <h1 className="flex items-center gap-2 text-2xl font-bold">
          <Ear className="size-6 text-brand-500" aria-hidden /> {t.title}
        </h1>
        <p className="max-w-3xl text-slate-600 dark:text-slate-300">{t.intro}</p>
        <LanguagePicker me={me} />
      </div>
      <Trainer key={language} language={language} />
    </AppShell>
  );
}
