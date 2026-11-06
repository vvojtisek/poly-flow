"use client";

import { Drama, Keyboard, ListChecks, RotateCcw, Users, Volume2 } from "lucide-react";
import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";

import { AnswerInput } from "@/components/AnswerInput";
import { AppShell, FullPageStatus, LanguagePicker } from "@/components/AppShell";
import { Kbd } from "@/components/Kbd";
import { TapText } from "@/components/TapText";
import { WordDiff } from "@/components/WordDiff";
import { Button, Notice } from "@/components/ui";
import {
  checkRoleplay,
  getRoleplay,
  listRoleplay,
  roleplayAudioUrl,
  type DictationResult,
  type Language,
  type RoleplayScene,
  type RoleplayScript,
} from "@/lib/api";
import { play, playToEnd, stop } from "@/lib/audio";
import { useAuth, useRequireMe } from "@/lib/auth";
import { cs } from "@/lib/i18n/cs";
import { useHotkeys } from "@/lib/keyboard";

const t = cs.roleplay;
const BUBBLE_COLORS = [
  "bg-sky-100 text-sky-950 dark:bg-sky-950 dark:text-sky-50",
  "bg-violet-100 text-violet-950 dark:bg-violet-950 dark:text-violet-50",
  "bg-emerald-100 text-emerald-950 dark:bg-emerald-950 dark:text-emerald-50",
];

function Bubble({
  script,
  index,
  language,
}: {
  script: RoleplayScript;
  index: number;
  language: Language;
}) {
  const line = script.lines[index]!;
  const [showCs, setShowCs] = useState(false);
  const other = script.speakers.filter((s) => s !== script.role).indexOf(line.speaker);
  return (
    <li className={`flex flex-col gap-1 motion-safe:animate-pop-in ${line.mine ? "items-end" : "items-start"}`}>
      <span className="px-2 text-xs font-semibold text-slate-500">{line.speaker}</span>
      <div
        className={`flex max-w-[85%] items-start gap-2 rounded-2xl px-4 py-2 ${
          line.mine ? "rounded-br-sm bg-brand-500 text-white" : `rounded-bl-sm ${BUBBLE_COLORS[other % BUBBLE_COLORS.length]}`
        }`}
      >
        <p lang={language} className="text-lg">
          <TapText text={line.text} language={language} />
        </p>
        <button
          type="button"
          aria-label={cs.audio.play}
          onClick={() => void play(roleplayAudioUrl(script.id, index))}
          className="mt-1 shrink-0 opacity-70 hover:opacity-100"
        >
          <Volume2 className="size-4" aria-hidden />
        </button>
      </div>
      {showCs ? (
        <span className="px-2 text-xs text-slate-500">{line.cs}</span>
      ) : (
        <button type="button" onClick={() => setShowCs(true)} className="px-2 text-xs text-slate-400 underline-offset-2 hover:underline">
          {t.showCs}
        </button>
      )}
    </li>
  );
}

function MyTurn({
  script,
  index,
  language,
  onDone,
}: {
  script: RoleplayScript;
  index: number;
  language: Language;
  onDone: (firstTry: boolean) => void;
}) {
  const line = script.lines[index]!;
  const [mode, setMode] = useState<"choose" | "type">("choose");
  const [wrong, setWrong] = useState<number[]>([]);
  const [text, setText] = useState("");
  const [result, setResult] = useState<DictationResult["marks"] | null>(null);
  const [busy, setBusy] = useState(false);
  useHotkeys();

  const pick = useCallback(
    (i: number) => {
      if (!line.options || wrong.includes(i)) return;
      if (i === line.answer) onDone(wrong.length === 0);
      else setWrong((w) => [...w, i]);
    },
    [line, wrong, onDone],
  );

  useEffect(() => {
    if (mode !== "choose") return;
    function onKey(e: KeyboardEvent) {
      const el = e.target as HTMLElement | null;
      if (e.ctrlKey || e.metaKey || e.altKey || e.repeat || el?.closest("input, textarea, select")) return;
      if (/^[1-9]$/.test(e.key) && Number(e.key) <= (line.options?.length ?? 0)) {
        e.preventDefault();
        pick(Number(e.key) - 1);
      }
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [mode, pick, line.options]);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (result) {
      onDone(result.every((m) => m.verdict === "ok"));
      return;
    }
    if (!text.trim()) return;
    setBusy(true);
    try {
      setResult((await checkRoleplay(script.id, index, text)).marks);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="flex flex-col gap-3 rounded-2xl border-2 border-brand-500/40 bg-white p-4 dark:bg-slate-900" aria-label={t.yourTurn}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm">
          <span className="text-slate-500">{t.want}</span> <strong>{line.cs}</strong>
        </p>
        <div role="tablist" className="flex gap-1">
          {(["choose", "type"] as const).map((m) => (
            <button
              key={m}
              type="button"
              role="tab"
              aria-selected={mode === m}
              onClick={() => setMode(m)}
              className={`inline-flex items-center gap-1 rounded-lg px-2 py-1 text-xs font-semibold ${
                mode === m ? "bg-brand-500 text-white" : "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-200"
              }`}
            >
              {m === "choose" ? <ListChecks className="size-3.5" aria-hidden /> : <Keyboard className="size-3.5" aria-hidden />}
              {m === "choose" ? t.choose : t.type}
            </button>
          ))}
        </div>
      </div>
      {mode === "choose" ? (
        <div className="flex flex-col gap-2">
          {line.options?.map((o, i) => (
            <button
              key={o}
              type="button"
              disabled={wrong.includes(i)}
              onClick={() => pick(i)}
              lang={language}
              className={`flex items-center gap-3 rounded-xl border-2 px-4 py-3 text-left text-lg transition-colors ${
                wrong.includes(i)
                  ? "border-rose-300 bg-rose-50 text-rose-800 line-through opacity-60 motion-safe:animate-pop-in dark:bg-rose-950/40 dark:text-rose-200"
                  : "border-slate-200 hover:border-brand-500 dark:border-slate-700"
              }`}
            >
              <Kbd>{String(i + 1)}</Kbd>
              {o}
            </button>
          ))}
          {wrong.length > 0 && <p className="text-sm text-rose-700 dark:text-rose-300">{t.tryAgain}</p>}
        </div>
      ) : (
        <form onSubmit={submit} className="flex flex-col gap-3">
          <AnswerInput language={language} value={text} onChange={setText} disabled={!!result || busy} placeholder={t.typePlaceholder} />
          {result && (
            <>
              <WordDiff marks={result} />
              <p lang={language} className="text-sm text-slate-600 dark:text-slate-300">
                <TapText text={line.text} language={language} />
              </p>
            </>
          )}
          <Button type="submit" data-hotkey="enter" disabled={busy || (!result && !text.trim())}>
            {result ? t.continue : t.check}
          </Button>
        </form>
      )}
    </section>
  );
}

function Stage({
  script,
  language,
  onRestart,
  onRole,
  onExit,
}: {
  script: RoleplayScript;
  language: Language;
  onRestart: () => void;
  onRole: (r: string) => void;
  onExit: () => void;
}) {
  const [shown, setShown] = useState(0); // lines on screen
  const [firstTry, setFirstTry] = useState(0);
  const end = useRef<HTMLDivElement>(null);
  const total = script.lines.filter((l) => l.mine).length;
  const next = script.lines[shown];
  const finished = shown >= script.lines.length;

  // The partner speaks: show the line, play it, then move on. Without TTS, a reading pause.
  useEffect(() => {
    if (!next || next.mine) return;
    let cancelled = false;
    const startedAt = Date.now();
    void (async () => {
      await new Promise((r) => setTimeout(r, 350));
      if (cancelled) return;
      await playToEnd(roleplayAudioUrl(script.id, shown));
      const minimum = 900 + next.text.length * 45;
      const wait = Math.max(250, minimum - (Date.now() - startedAt));
      await new Promise((r) => setTimeout(r, wait));
      if (!cancelled) setShown((n) => n + 1);
    })();
    return () => {
      cancelled = true;
    };
  }, [next, shown, script.id]);

  useEffect(() => {
    end.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [shown]);

  useEffect(() => () => stop(), []);

  const visible = next && !next.mine ? shown + 1 : shown;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-lg font-bold">{script.title}</h2>
        <span className="rounded-full bg-brand-500/10 px-3 py-1 text-sm font-semibold text-brand-600 dark:text-brand-50">
          {t.youAre(script.role)}
        </span>
      </div>
      <ol className="flex flex-col gap-3">
        {script.lines.slice(0, visible).map((_, i) => (
          <Bubble key={i} script={script} index={i} language={language} />
        ))}
      </ol>
      {next?.mine && (
        <MyTurn
          key={shown}
          script={script}
          index={shown}
          language={language}
          onDone={(ok) => {
            if (ok) setFirstTry((n) => n + 1);
            void play(roleplayAudioUrl(script.id, shown));
            setShown((n) => n + 1);
          }}
        />
      )}
      {finished && (
        <section className="flex flex-col items-center gap-3 rounded-3xl bg-gradient-to-br from-brand-500/10 to-emerald-400/10 p-6 text-center motion-safe:animate-pop-in">
          <p className="text-2xl font-bold">{t.done}</p>
          <p className="text-sm text-slate-600 dark:text-slate-300">{t.doneHelp(firstTry, total)}</p>
          <div className="flex flex-wrap justify-center gap-2">
            <Button onClick={onRestart}>
              <RotateCcw className="size-4" aria-hidden /> {t.again}
            </Button>
            {script.speakers
              .filter((s) => s !== script.role)
              .map((s) => (
                <Button key={s} variant="secondary" onClick={() => onRole(s)}>
                  <Users className="size-4" aria-hidden /> {t.otherRole(s)}
                </Button>
              ))}
            <Button variant="ghost" onClick={onExit}>
              {t.otherScene}
            </Button>
          </div>
        </section>
      )}
      <div ref={end} />
      <p className="hidden text-center text-xs text-slate-500 lg:block">{t.keys}</p>
    </div>
  );
}

function Roleplay({ language }: { language: Language }) {
  const [scenes, setScenes] = useState<RoleplayScene[] | null>(null);
  const [failed, setFailed] = useState(false);
  const [chosen, setChosen] = useState<{ scene: RoleplayScene; role: string; run: number } | null>(null);
  const [script, setScript] = useState<RoleplayScript | null>(null);

  useEffect(() => {
    let cancelled = false;
    listRoleplay(language)
      .then((s) => !cancelled && setScenes(s))
      .catch(() => !cancelled && setFailed(true));
    return () => {
      cancelled = true;
    };
  }, [language]);

  useEffect(() => {
    if (!chosen) return;
    let cancelled = false;
    setScript(null);
    getRoleplay(chosen.scene.id, chosen.role)
      .then((s) => !cancelled && setScript(s))
      .catch(() => !cancelled && setFailed(true));
    return () => {
      cancelled = true;
    };
  }, [chosen]);

  if (failed) return <Notice tone="error">{cs.common.error}</Notice>;
  if (!scenes) return <p className="text-sm text-slate-500">{cs.common.loading}</p>;
  if (!scenes.length) return <Notice>{t.empty}</Notice>;

  if (chosen) {
    if (!script) return <p className="text-sm text-slate-500">{cs.common.loading}</p>;
    return (
      <Stage
        key={`${script.id}:${script.role}:${chosen.run}`}
        script={script}
        language={language}
        onRestart={() => setChosen({ ...chosen, run: chosen.run + 1 })}
        onRole={(role) => setChosen({ scene: chosen.scene, role, run: chosen.run + 1 })}
        onExit={() => {
          setChosen(null);
          setScript(null);
        }}
      />
    );
  }

  return (
    <section className="flex flex-col gap-3">
      <h2 className="font-semibold">{t.pickScene}</h2>
      <ul className="grid gap-3 sm:grid-cols-2">
        {scenes.map((s) => (
          <li key={s.id} className="flex flex-col gap-3 rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
            <div>
              <p className="font-semibold">{s.title}</p>
              <p className="text-xs text-slate-500">
                {s.speakers.join(" · ")} · {t.lines(s.lines)}
              </p>
            </div>
            <div className="flex flex-wrap gap-2" aria-label={t.pickRole}>
              {s.speakers.map((r) => (
                <Button key={r} variant="secondary" className="!px-3 !py-1.5 text-sm" onClick={() => setChosen({ scene: s, role: r, run: 0 })}>
                  {r}
                </Button>
              ))}
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}

export default function RoleplayPage() {
  const me = useRequireMe();
  const { state } = useAuth();
  if (state.kind === "error") return <FullPageStatus text={cs.common.offline} />;
  if (!me) return <FullPageStatus text={cs.common.loading} />;
  const language = me.acting.active_language;
  return (
    <AppShell me={me}>
      <section className="mx-auto flex w-full max-w-3xl flex-col gap-4">
        <h1 className="flex items-center gap-2 text-2xl font-bold">
          <Drama className="size-6 text-brand-500" aria-hidden />
          {t.title}
        </h1>
        <p className="text-slate-600 dark:text-slate-300">{t.intro}</p>
        <LanguagePicker me={me} />
        <Roleplay key={`${me.acting.id}:${language}`} language={language} />
      </section>
    </AppShell>
  );
}
