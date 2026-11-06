"use client";

import { Headphones } from "lucide-react";
import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";

import { AnswerInput } from "@/components/AnswerInput";
import { AppShell, FullPageStatus, LanguagePicker } from "@/components/AppShell";
import { PlayButton, SlowToggle } from "@/components/PlayButton";
import { WordDiff } from "@/components/WordDiff";
import { Button, Notice } from "@/components/ui";
import {
  checkDictation,
  getDictationNext,
  myWordAudioUrl,
  type DictationNext,
  type DictationResult,
  type Language,
} from "@/lib/api";
import { play } from "@/lib/audio";
import { useAuth, useRequireMe } from "@/lib/auth";
import { cs } from "@/lib/i18n/cs";
import { useHotkeys } from "@/lib/keyboard";

const t = cs.dictation;

function Dictation({ language }: { language: Language }) {
  const [next, setNext] = useState<DictationNext | null>(null);
  const [text, setText] = useState("");
  const [result, setResult] = useState<DictationResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);
  const [scores, setScores] = useState<number[]>([]);
  const seen = useRef<string[]>([]);
  const input = useRef<HTMLInputElement>(null);
  useHotkeys();

  const load = useCallback(
    async (autoplay: boolean) => {
      setFailed(false);
      setResult(null);
      setText("");
      try {
        let n = await getDictationNext(language, seen.current);
        if (!n.item_id && n.pool > 0) {
          // Every sentence was used this session: start the round again.
          seen.current = [];
          n = await getDictationNext(language, []);
        }
        setNext(n);
        if (n.item_id) {
          seen.current.push(n.item_id);
          // Only after a click or key press; a fresh page load would be blocked by the browser.
          if (autoplay) void play(myWordAudioUrl(n.item_id, "example"));
          requestAnimationFrame(() => input.current?.focus());
        }
      } catch {
        setFailed(true);
      }
    },
    [language],
  );

  useEffect(() => {
    seen.current = [];
    setScores([]);
    void load(false);
  }, [load]);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!next?.item_id || busy) return;
    if (result) {
      await load(true);
      return;
    }
    if (!text.trim()) return;
    setBusy(true);
    try {
      const r = await checkDictation(next.item_id, text);
      setResult(r);
      setScores((s) => [...s, r.score]);
    } catch {
      setFailed(true);
    } finally {
      setBusy(false);
    }
  }

  if (failed) return <Notice tone="error">{cs.common.error}</Notice>;
  if (!next) return <p className="text-sm text-slate-500">{cs.common.loading}</p>;
  if (!next.item_id) return <Notice>{t.empty}</Notice>;

  const url = myWordAudioUrl(next.item_id, "example");
  const avg = scores.length ? Math.round((scores.reduce((a, b) => a + b, 0) / scores.length) * 100) : 0;
  const pct = result ? Math.round(result.score * 100) : 0;

  return (
    <form onSubmit={submit} className="flex flex-col gap-4">
      <div className="flex flex-col items-center gap-2 rounded-2xl bg-brand-500/5 p-4">
        <div className="flex items-center gap-3">
          <PlayButton url={url} label={t.listenAgain} hotkey />
          <SlowToggle />
        </div>
        <p className="text-sm text-slate-500">{t.words(next.words)}</p>
      </div>
      <AnswerInput
        ref={input}
        language={language}
        value={text}
        onChange={setText}
        disabled={!!result || busy}
        placeholder={t.placeholder}
      />
      {result && (
        <section className="flex flex-col gap-3 rounded-2xl border border-slate-200 p-4 dark:border-slate-800" aria-live="polite">
          <p className={`text-lg font-bold ${pct === 100 ? "text-emerald-600" : "text-slate-700 dark:text-slate-200"}`}>
            {pct === 100 ? t.perfect : t.score(pct)}
          </p>
          <WordDiff marks={result.marks} />
          <div className="text-sm">
            <p className="text-slate-500">{t.sentence}</p>
            <p lang={language} className="text-lg">
              {result.sentence}
            </p>
          </div>
          <p className="text-sm text-slate-600 dark:text-slate-300">
            {t.word}: <strong lang={language}>{result.lemma}</strong> = {result.translation}
          </p>
        </section>
      )}
      <Button type="submit" data-hotkey="enter" className="w-full !py-3 text-lg" disabled={busy || (!result && !text.trim())}>
        {result ? t.next : t.check}
      </Button>
      <p className="text-center text-xs text-slate-500">
        {scores.length > 0 && `${t.session(scores.length, avg)} · `}
        {t.keys}
      </p>
    </form>
  );
}

export default function DictationPage() {
  const me = useRequireMe();
  const { state } = useAuth();
  if (state.kind === "error") return <FullPageStatus text={cs.common.offline} />;
  if (!me) return <FullPageStatus text={cs.common.loading} />;
  const language = me.acting.active_language;
  return (
    <AppShell me={me}>
      <section className="mx-auto flex w-full max-w-2xl flex-col gap-4">
        <h1 className="flex items-center gap-2 text-2xl font-bold">
          <Headphones className="size-6 text-brand-500" aria-hidden />
          {t.title}
        </h1>
        <p className="text-slate-600 dark:text-slate-300">{t.intro}</p>
        <LanguagePicker me={me} />
        <Dictation key={`${me.acting.id}:${language}`} language={language} />
      </section>
    </AppShell>
  );
}
