"use client";

import { ChevronLeft, ChevronRight, Eye, EyeOff, Mic, Square, Volume2, Waves, type LucideIcon } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { AppShell, FullPageStatus, LanguagePicker } from "@/components/AppShell";
import { Kbd } from "@/components/Kbd";
import { PlayButton, SlowToggle } from "@/components/PlayButton";
import { Notice } from "@/components/ui";
import { useRecorder } from "@/hooks/useRecorder";
import { getPracticeSentences, getRoleplay, listRoleplay, myWordAudioUrl, roleplayAudioUrl, type Language, type RoleplayScene } from "@/lib/api";
import { clipSrc, play, playToEnd, stop } from "@/lib/audio";
import { useAuth, useRequireMe } from "@/lib/auth";
import { envelopeFromUrl, type Envelope } from "@/lib/envelope";
import { cs } from "@/lib/i18n/cs";

const t = cs.shadow;
const MAX_RECORDING_MS = 15000;

/** One line to shadow, from either source: a lesson word's example or a scene's dialogue line. */
type Line = { key: string; text: string; audio: string; cs?: string; speaker?: string; word?: { lemma: string; translation: string } };
type Source = { kind: "words" } | { kind: "scene"; id: string };

async function loadLines(language: Language, source: Source): Promise<Line[]> {
  if (source.kind === "words") {
    const list = await getPracticeSentences(language);
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

function Shadowing({ language, source }: { language: Language; source: Source }) {
  const [list, setList] = useState<Line[] | null>(null);
  const [failed, setFailed] = useState(false);
  const [index, setIndex] = useState(0);
  const [hidden, setHidden] = useState(false);
  const [mineUrl, setMineUrl] = useState<string | null>(null);
  const [tries, setTries] = useState(0);
  const [model, setModel] = useState<Envelope | null>(null);
  const [mine, setMine] = useState<Envelope | null>(null);
  const [noModel, setNoModel] = useState(false);
  const urls = useRef<string[]>([]);

  const onRecording = useCallback((blob: Blob) => {
    const url = URL.createObjectURL(blob);
    urls.current.push(url);
    setMineUrl(url);
    setTries((n) => n + 1);
    void envelopeFromUrl(url).then(setMine);
  }, []);
  const rec = useRecorder(onRecording, MAX_RECORDING_MS);
  const recording = rec.state.kind === "recording";

  useEffect(() => {
    let cancelled = false;
    loadLines(language, source)
      .then((l) => !cancelled && setList(l))
      .catch(() => !cancelled && setFailed(true));
    return () => {
      cancelled = true;
    };
    // The parent remounts this component per source, so the source object is stable here.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [language]);

  // Recordings live only in this tab; free them when leaving.
  useEffect(
    () => () => {
      for (const u of urls.current) URL.revokeObjectURL(u);
    },
    [],
  );

  const current = list?.[index];
  const modelUrl = current?.audio ?? null;

  useEffect(() => {
    setMineUrl(null);
    setMine(null);
    setModel(null);
    setNoModel(false);
    setTries(0);
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

  const go = useCallback(
    (delta: number) => {
      if (!list?.length || recording) return;
      stop();
      setIndex((i) => (i + delta + list.length) % list.length);
    },
    [list, recording],
  );

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const el = e.target as HTMLElement | null;
      if (e.ctrlKey || e.metaKey || e.altKey || e.repeat || el?.closest("input, select, textarea")) return;
      const actions: Record<string, () => void> = {
        KeyP: () => modelUrl && void play(modelUrl),
        KeyR: toggleRecord,
        KeyM: () => mineUrl && void play(mineUrl, { natural: true }),
        KeyC: () => void compare(),
        KeyN: () => go(1),
        KeyH: () => setHidden((h) => !h),
      };
      const run = actions[e.code];
      if (run) {
        e.preventDefault();
        run();
      }
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [modelUrl, mineUrl, toggleRecord, compare, go]);

  if (failed) return <Notice tone="error">{cs.common.error}</Notice>;
  if (!list) return <p className="text-sm text-slate-500">{cs.common.loading}</p>;
  if (!current || !modelUrl) return <Notice>{source.kind === "scene" ? t.sceneEmpty : t.empty}</Notice>;

  return (
    <div className="flex flex-col gap-4">
      <section className="flex flex-col gap-3 rounded-3xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <div className="flex items-center justify-between gap-2 text-sm text-slate-500">
          <span>
            {index + 1} / {list.length}
          </span>
          <span className="flex items-center gap-2">
            <SlowToggle />
            <button
              type="button"
              onClick={() => setHidden((h) => !h)}
              className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium dark:bg-slate-800"
            >
              {hidden ? <Eye className="size-3.5" aria-hidden /> : <EyeOff className="size-3.5" aria-hidden />}
              {hidden ? t.showText : t.hideText}
            </button>
          </span>
        </div>
        <div className="flex items-center gap-3">
          <PlayButton url={modelUrl} label={t.listen} />
          <div className="min-w-0">
            {current.speaker && <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{current.speaker}</p>}
            <p lang={language} className={`text-2xl font-medium leading-snug ${hidden ? "select-none blur-md" : ""}`}>
              {current.text}
            </p>
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
      <div className="flex justify-between gap-2">
        <button type="button" onClick={() => go(-1)} className="inline-flex items-center gap-1 rounded-lg px-3 py-2 text-sm text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800">
          <ChevronLeft className="size-4" aria-hidden /> {t.previous}
        </button>
        <button type="button" onClick={() => go(1)} className="inline-flex items-center gap-1 rounded-lg px-3 py-2 text-sm font-semibold text-brand-600 hover:bg-brand-500/10">
          {t.next} <ChevronRight className="size-4" aria-hidden /> <Kbd>N</Kbd>
        </button>
      </div>
      <p className="hidden text-center text-xs text-slate-500 lg:block">{t.keys}</p>
    </div>
  );
}

/** Which lines to shadow: example sentences of lesson words, or a whole dialogue from a met scene. */
function SourcePicker({ language, source, onChange }: { language: Language; source: Source; onChange: (s: Source) => void }) {
  const [scenes, setScenes] = useState<RoleplayScene[] | null>(null);
  useEffect(() => {
    let live = true;
    listRoleplay(language)
      .then((x) => live && setScenes(x))
      .catch(() => live && setScenes([]));
    return () => {
      live = false;
    };
  }, [language]);
  const sceneId = source.kind === "scene" ? source.id : "";
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
            onClick={() => kind === "words" ? onChange({ kind }) : scenes?.[0] && onChange({ kind, id: sceneId || scenes[0].id })}
            className={`rounded-full px-3 py-1 text-sm font-medium disabled:opacity-40 ${source.kind === kind ? "bg-brand-500 text-white" : "bg-slate-100 dark:bg-slate-800"}`}
          >
            {t.sources[kind]}
          </button>
        ))}
      </div>
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
      {scenes !== null && scenes.length === 0 && <p className="text-xs text-slate-500">{t.noScenes}</p>}
    </div>
  );
}

export default function ShadowingPage() {
  const me = useRequireMe();
  const { state } = useAuth();
  const [source, setSource] = useState<Source>({ kind: "words" });
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
        <SourcePicker key={`${me.acting.id}:${language}`} language={language} source={source} onChange={setSource} />
        <Shadowing key={`${me.acting.id}:${language}:${source.kind === "scene" ? source.id : "words"}`} language={language} source={source} />
      </section>
    </AppShell>
  );
}
