"use client";

import { ChevronLeft, ChevronRight, Eye, EyeOff, Mic, Repeat, Square, Volume2, Waves, type LucideIcon } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

import { AppShell, FullPageStatus, LanguagePicker } from "@/components/AppShell";
import { Kbd } from "@/components/Kbd";
import { digitOf, isTypingTarget } from "@/lib/keyboard";
import { PlayButton, SlowToggle } from "@/components/PlayButton";
import { Notice, RetryNotice, Skeleton } from "@/components/ui";
import { useRecorder } from "@/hooks/useRecorder";
import { getPracticeSentences, getRoleplay, listRoleplay, myWordAudioUrl, roleplayAudioUrl, type Language, type RoleplayScene } from "@/lib/api";
import { clipSrc, play, playToEnd, stop } from "@/lib/audio";
import { useAuth, useRequireMe } from "@/lib/auth";
import { envelopeFromUrl, type Envelope } from "@/lib/envelope";
import { cs } from "@/lib/i18n/cs";

const t = cs.shadow;
const MAX_RECORDING_MS = 15000;
/** Text support, from most to least: the whole line, first letters only, nothing (ear only). */
type Support = "full" | "hint" | "none";
const SUPPORTS: Support[] = ["full", "hint", "none"];
/** "Ich heiße Anna." -> "I__ h____ A___." : first letter and word length, punctuation kept. */
function hintText(text: string): string {
  return text.replace(/\p{L}+/gu, (word) => {
    const [first, ...rest] = Array.from(word);
    return first + rest.map(() => "_").join("");
  });
}
/** Echo round: time to repeat after the model, from the model's voiced length (or a default). */
function echoWindowMs(modelSeconds: number | undefined): number {
  const ms = Math.round(((modelSeconds ?? 3) * 1.5 + 1) * 1000);
  return Math.min(MAX_RECORDING_MS, Math.max(2000, ms));
}

/** One line to shadow, from either source: a lesson word's example or a scene's dialogue line. */
type Line = { key: string; text: string; audio: string; cs?: string; speaker?: string; word?: { lemma: string; translation: string } };
type Order = "recent" | "random";
type Source = { kind: "words"; order: Order } | { kind: "scene"; id: string };

async function loadLines(language: Language, source: Source): Promise<Line[]> {
  if (source.kind === "words") {
    const list = await getPracticeSentences(language, source.order);
    return list.map((x) => ({ key: x.item_id, text: x.sentence, audio: myWordAudioUrl(x.item_id, "example"), word: { lemma: x.lemma, translation: x.translation } }));
  }
  // The role only decides which lines roleplay quizzes; shadowing repeats every line in order.
  const scenes = await listRoleplay(language);
  const scene = scenes.find((x) => x.id === source.id);
  const role = scene?.speakers[0];
  if (!scene || !role) return [];
  const script = await getRoleplay(scene.id, role);
  return script.lines.map((l, i) => ({ key: `${scene.id}:${i}`, text: l.text, cs: l.cs, speaker: l.speaker, audio: roleplayAudioUrl(scene.id, i) }));
}

/** Two loudness outlines on a shared time axis: the model above, the learner below. */
function Waves2({ model, mine }: { model: Envelope | null; mine: Envelope | null }) {
  const W = 600;
  const H = 70;
  const longest = Math.max(model?.seconds ?? 0, mine?.seconds ?? 0, 0.1);
  function bars(env: Envelope, up: boolean, cls: string) {
    const width = (env.seconds / longest) * W;
    const step = width / env.bins.length;
    return env.bins.map((v, i) => {
      const h = Math.max(1.5, v * (H / 2 - 4));
      return (
        <rect
          key={i}
          x={i * step}
          y={up ? H / 2 - h : H / 2}
          width={Math.max(1, step - 1)}
          height={h}
          rx={1}
          className={cls}
        />
      );
    });
  }
  return (
    <figure className="flex flex-col gap-1">
      <svg viewBox={`0 0 ${W} ${H}`} className="h-24 w-full" role="img" aria-label={t.waveHelp}>
        <line x1={0} x2={W} y1={H / 2} y2={H / 2} className="stroke-slate-300 dark:stroke-slate-700" />
        {model && bars(model, true, "fill-brand-500")}
        {mine && bars(mine, false, "fill-amber-500")}
      </svg>
      <figcaption className="flex flex-wrap items-center justify-between gap-2 text-xs text-slate-500">
        <span className="flex gap-3">
          <span className="flex items-center gap-1">
            <span className="inline-block size-2.5 rounded-sm bg-brand-500" aria-hidden /> {t.model}
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block size-2.5 rounded-sm bg-amber-500" aria-hidden /> {t.you}
          </span>
        </span>
        {model && mine && <span>{t.duration(model.seconds, mine.seconds)}</span>}
      </figcaption>
    </figure>
  );
}

function ActionButton({
  icon: Icon,
  label,
  onClick,
  disabled,
  tone = "secondary",
  kbd,
}: {
  icon: LucideIcon;
  label: string;
  onClick: () => void;
  disabled?: boolean;
  tone?: "primary" | "secondary" | "danger";
  kbd: string;
}) {
  const tones = {
    primary: "bg-brand-500 text-white hover:bg-brand-600",
    secondary: "bg-slate-100 text-slate-800 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-100 dark:hover:bg-slate-700",
    danger: "bg-rose-600 text-white motion-safe:animate-pulse",
  };
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={`flex flex-1 flex-col items-center gap-1 rounded-2xl px-3 py-3 text-sm font-semibold disabled:opacity-40 ${tones[tone]}`}
    >
      <Icon className="size-6" aria-hidden />
      <span>{label}</span>
      <span className="hidden opacity-70 lg:inline">
        <Kbd>{kbd}</Kbd>
      </span>
    </button>
  );
}

function Shadowing({ language, source, start, onIndex }: { language: Language; source: Source; start: number; onIndex: (i: number) => void }) {
  const [list, setList] = useState<Line[] | null>(null);
  const [failed, setFailed] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const [index, setIndex] = useState(start);
  const [support, setSupport] = useState<Support>("full");
  const cycleSupport = useCallback(() => setSupport((v) => SUPPORTS[(SUPPORTS.indexOf(v) + 1) % SUPPORTS.length] ?? "full"), []);
  const [mineUrl, setMineUrl] = useState<string | null>(null);
  // Recordings made per line in this visit (local only, never sent or scored).
  const [practiced, setPracticed] = useState<Record<number, number>>({});
  const indexRef = useRef(start);
  indexRef.current = index;
  const tries = practiced[index] ?? 0;
  const [model, setModel] = useState<Envelope | null>(null);
  const [mine, setMine] = useState<Envelope | null>(null);
  const [noModel, setNoModel] = useState(false);
  const urls = useRef<string[]>([]);
  // Echo round: listen, record for a window sized to the model, then hear both. null = off.
  const [echo, setEcho] = useState<null | "listen" | "speak" | "together" | "compare">(null);
  // "after": classic echo (listen, then repeat). "together": speak over the model as it plays,
  // the shadowing technique proper; needs headphones, or the microphone records the model too.
  const [echoMode, setEchoModeState] = useState<"after" | "together">("after");
  useEffect(() => {
    try {
      if (window.localStorage.getItem("polyflow.shadow.echoMode") === "together") setEchoModeState("together");
    } catch {
      /* storage blocked: keep the default */
    }
  }, []);
  function setEchoMode(value: "after" | "together") {
    setEchoModeState(value);
    try {
      window.localStorage.setItem("polyflow.shadow.echoMode", value);
    } catch {
      /* per-device convenience only */
    }
  }
  const echoPending = useRef(false);
  const echoTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const echoRun = useRef(0);
  // Continuous run: after each round, move to the next line and start its round, to the end.
  const [chain, setChain] = useState(false);
  const [advance, setAdvance] = useState(false);
  const chainNext = useRef<number | null>(null); // the line whose round starts on arrival

  const onRecording = useCallback((blob: Blob) => {
    const url = URL.createObjectURL(blob);
    urls.current.push(url);
    setMineUrl(url);
    const at = indexRef.current;
    setPracticed((p) => ({ ...p, [at]: (p[at] ?? 0) + 1 }));
    void envelopeFromUrl(url).then(setMine);
  }, []);
  const rec = useRecorder(onRecording, MAX_RECORDING_MS);
  const recording = rec.state.kind === "recording";

  useEffect(() => {
    let cancelled = false;
    setFailed(false);
    loadLines(language, source)
      .then((l) => {
        if (cancelled) return;
        setList(l);
        // A remembered line that no longer exists (fewer sentences now) falls back to the first.
        setIndex((i) => (i < l.length ? i : 0));
      })
      .catch(() => !cancelled && setFailed(true));
    return () => {
      cancelled = true;
    };
    // The parent remounts this component per source, so the source object is stable here.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [language, attempt]);

  // Recordings live only in this tab; free them when leaving.
  useEffect(
    () => () => {
      for (const u of urls.current) URL.revokeObjectURL(u);
    },
    [],
  );

  useEffect(() => {
    if (list) onIndex(index);
  }, [index, list, onIndex]);

  const current = list?.[index];
  const cueLine = index > 0 ? list?.[index - 1] : undefined;
  const modelUrl = current?.audio ?? null;

  useEffect(() => {
    setMineUrl(null);
    setMine(null);
    setModel(null);
    setNoModel(false);
    // Moving to another line abandons a running echo round.
    echoRun.current += 1;
    echoPending.current = false;
    if (echoTimer.current) clearTimeout(echoTimer.current);
    setEcho(null);
    if (!modelUrl) return;
    let cancelled = false;
    clipSrc(modelUrl)
      .then((src) => envelopeFromUrl(src))
      .then((e) => !cancelled && setModel(e))
      .catch(() => !cancelled && setNoModel(true));
    return () => {
      cancelled = true;
    };
  }, [modelUrl]);

  const toggleRecord = useCallback(() => {
    if (recording) rec.stop();
    else {
      stop();
      void rec.start();
    }
  }, [rec, recording]);

  const compare = useCallback(async () => {
    if (!modelUrl || !mineUrl) return;
    await playToEnd(modelUrl);
    await new Promise((r) => setTimeout(r, 250));
    await playToEnd(mineUrl, { natural: true });
  }, [modelUrl, mineUrl]);

  const runEcho = useCallback(async () => {
    if (!modelUrl || recording || echo) return;
    const run = ++echoRun.current;
    if (echoMode === "together") {
      // Record first so the learner's first syllable is not cut, then play the model under it.
      setEcho("together");
      echoPending.current = true;
      await rec.start();
      if (run !== echoRun.current) return;
      await playToEnd(modelUrl);
      if (run !== echoRun.current) return;
      echoTimer.current = setTimeout(() => rec.stop(), 700); // a short tail for the last word
      return;
    }
    setEcho("listen");
    await playToEnd(modelUrl);
    if (run !== echoRun.current) return; // the learner moved to another line meanwhile
    setEcho("speak");
    echoPending.current = true;
    await rec.start();
    echoTimer.current = setTimeout(() => rec.stop(), echoWindowMs(model?.seconds));
  }, [modelUrl, recording, echo, rec, model?.seconds, echoMode]);

  // The echo recording arrived: play the model and then the learner, and end the round.
  useEffect(() => {
    if (!mineUrl || !echoPending.current) return;
    echoPending.current = false;
    if (echoTimer.current) clearTimeout(echoTimer.current);
    setEcho("compare");
    const run = echoRun.current;
    void compare().finally(() => {
      setEcho(null);
      // Esc or a manual move during the compare step ends a continuous run too.
      if (chain && run === echoRun.current) setAdvance(true);
    });
  }, [mineUrl, compare, chain]);
  // A recorder failure (denied, unsupported) ends the round instead of leaving it hanging.
  useEffect(() => {
    if (rec.state.kind === "error" && echo) {
      echoPending.current = false;
      setEcho(null);
    }
  }, [rec.state.kind, echo]);
  useEffect(() => () => {
    if (echoTimer.current) clearTimeout(echoTimer.current);
  }, []);

  // In a dialogue the learner can take one character's part: only that speaker's lines are
  // practised, and the partner's preceding line is shown (and playable) as the cue.
  const [role, setRole] = useState<string | null>(null);
  const speakers = list ? [...new Set(list.flatMap((l) => (l.speaker ? [l.speaker] : [])))] : [];
  const isTarget = useCallback((i: number) => !role || list?.[i]?.speaker === role, [role, list]);
  const targets = list ? list.map((_, i) => i).filter(isTarget) : [];
  useEffect(() => {
    if (list && role && !isTarget(index)) {
      const first = list.findIndex((_, i) => isTarget(i));
      if (first >= 0) setIndex(first);
    }
  }, [role, list, index, isTarget]);
  const go = useCallback(
    (delta: number) => {
      if (!list?.length || recording) return;
      stop();
      setIndex((i) => {
        for (let step = 1; step <= list.length; step++) {
          const j = (((i + delta * step) % list.length) + list.length) % list.length;
          if (isTarget(j)) return j;
        }
        return i;
      });
    },
    [list, recording, isTarget],
  );
  const jump = useCallback(
    (i: number) => {
      if (recording || !isTarget(i)) return;
      stop();
      setIndex(i);
    },
    [recording, isTarget],
  );

  useEffect(() => {
    if (!advance) return;
    setAdvance(false);
    const last = targets[targets.length - 1];
    if (index === last) return; // the end of the list (or of the chosen role) ends the run
    const next = targets.find((i) => i > index) ?? targets[0];
    chainNext.current = next ?? null;
    go(1);
  }, [advance, index, targets, go]);
  useEffect(() => {
    // Only once the next line is actually current, so its round uses that line's audio.
    if (chainNext.current !== index || !modelUrl || echo || recording) return;
    // Cleared and re-armed if the line's model envelope arrives meanwhile (runEcho changes).
    const timer = setTimeout(() => {
      chainNext.current = null;
      void runEcho();
    }, 500);
    return () => clearTimeout(timer);
  }, [modelUrl, echo, recording, runEcho, index]);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.defaultPrevented || e.ctrlKey || e.metaKey || e.altKey || e.repeat || isTypingTarget(e.target)) return;
      const digit = digitOf(e);
      if (digit !== null && list && digit <= list.length) {
        e.preventDefault();
        jump(digit - 1);
        return;
      }
      const actions: Record<string, () => void> = {
        KeyP: () => modelUrl && void play(modelUrl),
        KeyR: toggleRecord,
        KeyM: () => mineUrl && void play(mineUrl, { natural: true }),
        KeyC: () => void compare(),
        KeyN: () => go(1),
        ArrowRight: () => go(1),
        KeyB: () => go(-1),
        ArrowLeft: () => go(-1),
        // Escape ends whatever is running: a recording (kept, as with R), an echo round, playback.
        Escape: () => {
          echoRun.current += 1;
          echoPending.current = false;
          if (echoTimer.current) clearTimeout(echoTimer.current);
          setEcho(null);
          if (recording) rec.stop();
          stop();
        },
        KeyH: cycleSupport,
        KeyA: () => void runEcho(),
      };
      const run = actions[e.code];
      if (run) {
        e.preventDefault();
        run();
      }
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [modelUrl, mineUrl, toggleRecord, compare, go, runEcho, jump, list, recording, rec]);

  if (failed) return <RetryNotice text={source.kind === "scene" ? t.sceneFailed : t.wordsFailed} onRetry={() => setAttempt((n) => n + 1)} />;
  if (!list)
    return (
      <div aria-busy className="flex flex-col gap-4">
        <div className="rounded-3xl border border-slate-200 p-5 dark:border-slate-800"><Skeleton lines={4} /></div>
        <div className="h-20 rounded-2xl bg-slate-100 motion-safe:animate-pulse dark:bg-slate-800" aria-hidden />
      </div>
    );
  if (!current || !modelUrl)
    return source.kind === "scene" ? (
      <Notice>{t.sceneEmpty}</Notice>
    ) : (
      <div className="flex flex-col items-start gap-3 rounded-2xl border border-dashed border-slate-300 p-5 dark:border-slate-700">
        <p className="text-sm text-slate-600 dark:text-slate-300">{t.empty}</p>
        <Link href="/lesson/vocabulary" className="inline-flex min-h-11 items-center rounded-xl bg-brand-500 px-4 py-2 font-semibold text-white hover:bg-brand-600">
          {t.emptyAction}
        </Link>
      </div>
    );

  return (
    <div className="flex flex-col gap-4">
      <section className="flex flex-col gap-3 rounded-3xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <div className="flex items-center justify-between gap-2 text-sm text-slate-500">
          <span>
            {index + 1} / {list.length}
            <span className="ml-2 text-xs">{t.recordedCount(targets.filter((i) => practiced[i]).length, targets.length)}</span>
          </span>
          <span className="flex items-center gap-2">
            <SlowToggle />
            <button
              type="button"
              onClick={cycleSupport}
              aria-label={t.supportButton(t.supports[support])}
              className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium dark:bg-slate-800"
            >
              {support === "none" ? <EyeOff className="size-3.5" aria-hidden /> : <Eye className="size-3.5" aria-hidden />}
              {t.supports[support]}
            </button>
          </span>
        </div>
        {role && cueLine && cueLine.speaker !== role && (
          <div className="flex items-center gap-2 rounded-xl bg-slate-50 px-3 py-2 text-sm dark:bg-slate-800/60">
            <PlayButton url={cueLine.audio} size="sm" label={t.cuePlay} />
            <span className="min-w-0">
              <span className="block text-xs text-slate-500">{t.cue(cueLine.speaker ?? "")}</span>
              <span lang={language} className="block">{cueLine.text}</span>
            </span>
          </div>
        )}
        <div className="flex items-center gap-3">
          <PlayButton url={modelUrl} label={t.listen} />
          <div className="min-w-0">
            {current.speaker && <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{current.speaker}</p>}
            {support === "full" && (
              <p lang={language} className="text-2xl font-medium leading-snug">
                {current.text}
              </p>
            )}
            {support === "hint" && (
              <p lang={language} aria-label={t.hintAria} className="font-mono text-2xl leading-snug tracking-wide">
                {hintText(current.text)}
              </p>
            )}
            {support === "none" && <p className="text-base italic text-slate-500">{t.earOnly}</p>}
          </div>
        </div>
        {current.cs && <p className="text-sm text-slate-600 dark:text-slate-300">{current.cs}</p>}
        {current.word && (
          <p className="text-sm text-slate-500">
            {t.word}: <strong lang={language}>{current.word.lemma}</strong> = {current.word.translation}
          </p>
        )}
        <Waves2 model={model} mine={mine} />
        <p className="text-xs text-slate-500">
          {t.waveHelp}
          {tries > 0 && ` · ${t.tries(tries)}`}
        </p>
      </section>

      {speakers.length > 1 && (
        <div role="radiogroup" aria-label={t.roleLabel} className="-mt-1 flex flex-wrap items-center gap-1 text-xs">
          <span className="mr-1 text-slate-500">{t.roleLabel}:</span>
          {[null, ...speakers].map((value) => (
            <button
              key={value ?? "all"}
              type="button"
              role="radio"
              aria-checked={role === value}
              onClick={() => setRole(value)}
              className={`rounded-full px-2.5 py-1 font-medium ${role === value ? "bg-slate-800 text-white dark:bg-slate-200 dark:text-slate-900" : "bg-slate-100 dark:bg-slate-800"}`}
            >
              {value ?? t.allRoles}
            </button>
          ))}
        </div>
      )}
      {/* Every line at a glance: filled once recorded in this visit; tap to jump. */}
      <nav aria-label={t.linesNav} className="-mt-1 flex flex-wrap gap-1.5">
        {list.map((line, i) => (
          <button
            key={line.key}
            type="button"
            onClick={() => jump(i)}
            disabled={!isTarget(i)}
            aria-current={i === index ? "true" : undefined}
            aria-label={t.lineDot(i + 1, Boolean(practiced[i]))}
            title={line.speaker ? `${line.speaker}: ${line.text}` : line.text}
            className={`size-7 rounded-full text-xs font-semibold focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 disabled:opacity-30 ${
              practiced[i] ? "bg-emerald-500 text-white" : "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300"
            } ${i === index ? "ring-2 ring-brand-500 ring-offset-1 dark:ring-offset-slate-950" : ""}`}
          >
            {i + 1}
          </button>
        ))}
      </nav>
      {targets.length > 0 && targets.every((i) => practiced[i]) && (
        <Notice>{source.kind === "scene" ? t.allRecordedScene : t.allRecorded}</Notice>
      )}

      {noModel && <Notice>{t.noModel}</Notice>}
      {rec.state.kind === "error" && (
        <Notice tone="error">{rec.state.reason === "denied" ? t.denied : t.unsupported}</Notice>
      )}

      <div className="flex gap-2">
        <ActionButton icon={Volume2} label={t.listen} onClick={() => void play(modelUrl)} kbd="P" />
        <ActionButton
          icon={recording ? Square : Mic}
          label={recording ? t.stop : t.record}
          onClick={toggleRecord}
          tone={recording ? "danger" : "primary"}
          kbd="R"
        />
        <ActionButton icon={Waves} label={t.mine} onClick={() => mineUrl && void play(mineUrl, { natural: true })} disabled={!mineUrl} kbd="M" />
        <ActionButton icon={Waves} label={t.compare} onClick={() => void compare()} disabled={!mineUrl || noModel} kbd="C" />
      </div>
      <button
        type="button"
        onClick={() => void runEcho()}
        disabled={Boolean(echo) || recording || noModel}
        className="flex min-h-11 items-center justify-center gap-2 rounded-2xl border border-brand-500/50 px-4 py-2 text-sm font-semibold text-brand-700 hover:bg-brand-500/5 disabled:opacity-60 dark:text-brand-100"
      >
        <Repeat className="size-4" aria-hidden />
        {echo ? t.echoSteps[echo] : t.echo}
        <span className="hidden lg:inline"><Kbd>A</Kbd></span>
      </button>
      <div role="radiogroup" aria-label={t.echoModeLabel} className="-mt-2 flex flex-wrap items-center justify-center gap-1 text-xs">
        {(["after", "together"] as const).map((value) => (
          <button
            key={value}
            type="button"
            role="radio"
            aria-checked={echoMode === value}
            disabled={Boolean(echo)}
            onClick={() => setEchoMode(value)}
            className={`rounded-full px-2.5 py-1 font-medium disabled:opacity-50 ${echoMode === value ? "bg-slate-800 text-white dark:bg-slate-200 dark:text-slate-900" : "bg-slate-100 dark:bg-slate-800"}`}
          >
            {t.echoModes[value]}
          </button>
        ))}
      </div>
      <label className="-mt-1 flex items-center justify-center gap-2 text-xs text-slate-600 dark:text-slate-300">
        <input type="checkbox" checked={chain} onChange={(e) => setChain(e.target.checked)} className="size-4 accent-brand-500" />
        {t.chain}
      </label>
      {echoMode === "together" && <p className="-mt-2 text-center text-xs text-slate-500">{t.headphones}</p>}
      <p className="sr-only" aria-live="polite">{echo ? t.echoSteps[echo] : ""}</p>
      <div className="flex justify-between gap-2">
        <button type="button" onClick={() => go(-1)} className="inline-flex items-center gap-1 rounded-lg px-3 py-2 text-sm text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800">
          <ChevronLeft className="size-4" aria-hidden /> {t.previous} <span className="hidden lg:inline"><Kbd>B</Kbd></span>
        </button>
        <button type="button" onClick={() => go(1)} className="inline-flex items-center gap-1 rounded-lg px-3 py-2 text-sm font-semibold text-brand-600 hover:bg-brand-500/10">
          {t.next} <ChevronRight className="size-4" aria-hidden /> <span className="hidden lg:inline"><Kbd>N</Kbd></span>
        </button>
      </div>
      <p className="hidden text-center text-xs text-slate-500 lg:block">{t.keys}</p>
    </div>
  );
}

/** Which lines to shadow: example sentences of lesson words, or a whole dialogue from a met scene. */
function SourcePicker({ language, source, onChange }: { language: Language; source: Source; onChange: (s: Source) => void }) {
  const [scenes, setScenes] = useState<RoleplayScene[] | null>(null);
  // A failed list is not "no scenes yet": that would tell the learner to do lessons they did.
  const [scenesFailed, setScenesFailed] = useState(false);
  const [scenesAttempt, setScenesAttempt] = useState(0);
  useEffect(() => {
    let live = true;
    setScenesFailed(false);
    listRoleplay(language)
      .then((x) => live && setScenes(x))
      .catch(() => live && setScenesFailed(true));
    return () => {
      live = false;
    };
  }, [language, scenesAttempt]);
  const sceneId = source.kind === "scene" ? source.id : "";
  // A scene from a link or an old URL that this profile cannot open (not met yet, hidden by the
  // child filter, or another language): fall back to the first open scene, or to words, and say so.
  const [replaced, setReplaced] = useState<null | "scene" | "words">(null);
  useEffect(() => {
    if (!scenes || source.kind !== "scene" || scenes.some((x) => x.id === source.id)) return;
    setReplaced(scenes[0] ? "scene" : "words");
    onChange(scenes[0] ? { kind: "scene", id: scenes[0].id } : { kind: "words", order: "recent" });
  }, [scenes, source, onChange]);
  // Coming back from a scene keeps the word order the learner chose before.
  const lastOrder = useRef<Order>("recent");
  if (source.kind === "words") lastOrder.current = source.order;
  return (
    <div className="flex flex-col gap-2">
      <div role="radiogroup" aria-label={t.sourceLabel} className="flex flex-wrap gap-1">
        {(["words", "scene"] as const).map((kind) => (
          <button
            key={kind}
            type="button"
            role="radio"
            aria-checked={source.kind === kind}
            disabled={kind === "scene" && !scenes?.length}
            onClick={() => kind === "words" ? onChange({ kind, order: lastOrder.current }) : scenes?.[0] && onChange({ kind, id: sceneId || scenes[0].id })}
            className={`rounded-full px-3 py-1 text-sm font-medium disabled:opacity-40 ${source.kind === kind ? "bg-brand-500 text-white" : "bg-slate-100 dark:bg-slate-800"}`}
          >
            {t.sources[kind]}
          </button>
        ))}
      </div>
      {source.kind === "words" && (
        <div role="radiogroup" aria-label={t.orderLabel} className="flex flex-wrap items-center gap-1 text-xs">
          <span className="mr-1 text-slate-500">{t.orderLabel}:</span>
          {(["recent", "random"] as const).map((order) => (
            <button
              key={order}
              type="button"
              role="radio"
              aria-checked={source.order === order}
              onClick={() => onChange({ kind: "words", order })}
              className={`rounded-full px-2.5 py-1 font-medium ${source.order === order ? "bg-slate-800 text-white dark:bg-slate-200 dark:text-slate-900" : "bg-slate-100 dark:bg-slate-800"}`}
            >
              {t.orders[order]}
            </button>
          ))}
        </div>
      )}
      {source.kind === "scene" && scenes && scenes.length > 0 && (
        <label className="flex flex-col gap-1 text-sm">
          <span className="text-slate-500">{t.scenePick}</span>
          <select
            value={sceneId}
            onChange={(e) => onChange({ kind: "scene", id: e.target.value })}
            className="min-h-11 rounded-xl border border-slate-300 bg-white px-3 dark:border-slate-700 dark:bg-slate-900"
          >
            {scenes.map((x) => (
              <option key={x.id} value={x.id}>
                {t.sceneOption(x.title, x.lines)}
              </option>
            ))}
          </select>
        </label>
      )}
      {replaced && <p className="text-xs text-amber-700 dark:text-amber-300">{replaced === "scene" ? t.sceneReplaced : t.sceneReplacedWords}</p>}
      {scenes !== null && scenes.length === 0 && <p className="text-xs text-slate-500">{t.noScenes}</p>}
      {scenesFailed && (
        <p className="flex flex-wrap items-center gap-2 text-xs text-red-700 dark:text-red-300">
          {t.scenesFailed}
          <button type="button" onClick={() => setScenesAttempt((n) => n + 1)} className="font-semibold underline">
            {cs.common.retry}
          </button>
        </p>
      )}
    </div>
  );
}

export default function ShadowingPage() {
  const me = useRequireMe();
  const { state } = useAuth();
  const [source, setSourceState] = useState<Source>({ kind: "words", order: "recent" });
  const [start, setStart] = useState(0);
  const [ready, setReady] = useState(false);
  // The source and line live in the URL, so a reload or Back returns to the same sentence.
  useEffect(() => {
    const q = new URLSearchParams(window.location.search);
    const scene = q.get("scene");
    if (scene && /^[0-9a-f-]{36}$/i.test(scene)) setSourceState({ kind: "scene", id: scene });
    else if (q.get("order") === "random") setSourceState({ kind: "words", order: "random" });
    const line = Number(q.get("line"));
    if (Number.isInteger(line) && line > 0 && line < 200) setStart(line - 1);
    setReady(true);
  }, []);
  const writeUrl = useCallback((next: Source, index: number) => {
    const q = new URLSearchParams(window.location.search);
    q.delete("scene");
    q.delete("order");
    q.delete("line");
    if (next.kind === "scene") q.set("scene", next.id);
    else if (next.order === "random") q.set("order", "random");
    // A random sample differs on every load, so only a stable list remembers its line.
    if (index > 0 && (next.kind === "scene" || next.order === "recent")) q.set("line", String(index + 1));
    const qs = q.toString();
    window.history.replaceState(window.history.state, "", `${window.location.pathname}${qs ? `?${qs}` : ""}`);
  }, []);
  const setSource = useCallback((next: Source) => {
    setSourceState(next);
    setStart(0);
    writeUrl(next, 0);
  }, [writeUrl]);
  const onIndex = useCallback((i: number) => writeUrl(source, i), [source, writeUrl]);
  // A scene belongs to one language: switching language goes back to that language's words.
  const activeLanguage = me?.acting.active_language;
  const seenLanguage = useRef(activeLanguage);
  useEffect(() => {
    if (seenLanguage.current && activeLanguage && seenLanguage.current !== activeLanguage && source.kind === "scene") {
      setSource({ kind: "words", order: "recent" });
    }
    seenLanguage.current = activeLanguage;
  }, [activeLanguage, source.kind, setSource]);
  if (state.kind === "error") return <FullPageStatus text={cs.common.offline} />;
  if (!me) return <FullPageStatus text={cs.common.loading} />;
  const language = me.acting.active_language;
  return (
    <AppShell me={me}>
      <section className="mx-auto flex w-full max-w-2xl flex-col gap-4">
        <h1 className="flex items-center gap-2 text-2xl font-bold">
          <Waves className="size-6 text-brand-500" aria-hidden />
          {t.title}
        </h1>
        <p className="text-slate-600 dark:text-slate-300">{t.intro}</p>
        <LanguagePicker me={me} />
        {ready && (
          <>
            <SourcePicker key={`${me.acting.id}:${language}`} language={language} source={source} onChange={setSource} />
            <Shadowing key={`${me.acting.id}:${language}:${source.kind === "scene" ? source.id : source.order}`} language={language} source={source} start={start} onIndex={onIndex} />
          </>
        )}
      </section>
    </AppShell>
  );
}
