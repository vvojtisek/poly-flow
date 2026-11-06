"use client";

import { AudioLines, CheckCircle2, Ear, Search, XCircle } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { AppShell, FullPageStatus, LanguagePicker } from "@/components/AppShell";
import { PlayButton } from "@/components/PlayButton";
import { Button, Notice } from "@/components/ui";
import { getSounds, myWordAudioUrl, type Language, type SoundExample, type SoundRule } from "@/lib/api";
import { play, useClipState } from "@/lib/audio";
import { useAuth, useRequireMe } from "@/lib/auth";
import { cs } from "@/lib/i18n/cs";
import { fold } from "@/lib/palette";

const t = cs.sounds;

function Example({ ex, language }: { ex: SoundExample; language: Language }) {
  return (
    <li className="flex items-center gap-2 rounded-xl bg-slate-50 px-3 py-2 dark:bg-slate-800/60">
      <span className="flex min-w-0 flex-col">
        <span lang={language} className="text-lg">
          {ex.lemma.slice(0, ex.start)}
          <mark className="rounded bg-brand-500/20 px-0.5 font-bold text-brand-600 dark:text-brand-50">{ex.lemma.slice(ex.start, ex.end)}</mark>
          {ex.lemma.slice(ex.end)}
        </span>
        <span className="truncate text-xs text-slate-500">
          {ex.translation}
          {ex.met && <span className="ml-1 text-emerald-600"> · {t.known}</span>}
        </span>
      </span>
      {ex.met && (
        <span className="ml-auto">
          <PlayButton url={myWordAudioUrl(ex.id)} label={cs.audio.playWord} size="sm" />
        </span>
      )}
    </li>
  );
}

function Rule({ rule, language }: { rule: SoundRule; language: Language }) {
  return (
    <article className="flex flex-col gap-3 rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
      <header className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <h2 lang={language} className="text-2xl font-bold">
          {rule.spelling}
        </h2>
        <span className="text-sm text-slate-500">{t.sounds}</span>
        <span className="rounded-lg bg-brand-500/10 px-2 py-0.5 font-semibold text-brand-600 dark:text-brand-50">{rule.czech}</span>
      </header>
      <p className="text-sm text-slate-700 dark:text-slate-200">{rule.note}</p>
      {rule.examples.length ? (
        <ul className="grid gap-2 sm:grid-cols-2">
          {rule.examples.map((ex) => (
            <Example key={ex.id} ex={ex} language={language} />
          ))}
        </ul>
      ) : (
        <p className="text-xs text-slate-500">{t.noExamples}</p>
      )}
    </article>
  );
}

type SoundQuestion = { answer: SoundRule; example: SoundExample; options: SoundRule[] };

function pickQuestion(rules: SoundRule[], previous?: string): SoundQuestion | null {
  const eligible = rules.filter((rule) => rule.examples.some((example) => example.met));
  if (eligible.length < 2) return null;
  const pool = eligible.filter((rule) => rule.id !== previous);
  const answer = pool[Math.floor(Math.random() * pool.length)] ?? eligible[0]!;
  const examples = answer.examples.filter((example) => example.met);
  const example = examples[Math.floor(Math.random() * examples.length)]!;
  const distractors = eligible.filter((rule) => rule.id !== answer.id);
  const options = [answer, ...distractors.sort(() => Math.random() - 0.5).slice(0, 3)];
  return { answer, example, options: options.sort(() => Math.random() - 0.5) };
}

function SoundQuiz({ rules, language }: { rules: SoundRule[]; language: Language }) {
  const [question, setQuestion] = useState(() => pickQuestion(rules));
  const [chosen, setChosen] = useState<string | null>(null);
  const [round, setRound] = useState(1);
  const audioUrl = question ? myWordAudioUrl(question.example.id) : "";
  const audio = useClipState(audioUrl);

  useEffect(() => {
    if (audioUrl) void play(audioUrl);
  }, [audioUrl]);

  if (!question) return <Notice>{t.quizNeedsExamples}</Notice>;

  function next() {
    const previous = question?.answer.id;
    if (!previous) return;
    setQuestion(pickQuestion(rules, previous));
    setChosen(null);
    setRound((value) => value + 1);
  }

  const correct = chosen === question.answer.id;
  return (
    <section className="flex flex-col gap-4 rounded-3xl border border-brand-500/30 bg-gradient-to-br from-brand-500/10 to-white p-4 dark:to-slate-900" aria-labelledby="sound-quiz-title">
      <header>
        <h2 id="sound-quiz-title" className="flex items-center gap-2 text-lg font-bold"><Ear className="size-5 text-brand-500" aria-hidden />{t.quizTitle}</h2>
        <p className="text-sm text-slate-600 dark:text-slate-300">{t.quizHelp}</p>
      </header>
      <div className="flex flex-wrap items-center gap-3">
        <Button variant="secondary" onClick={() => void play(audioUrl)}>{cs.audio.playWord}</Button>
        {audio === "error" && <span className="text-sm text-rose-700 dark:text-rose-300">{t.quizAudioFailed}</span>}
        <span className="text-sm text-slate-500">{t.quizRound(round)}</span>
      </div>
      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4" role="group" aria-label={t.quizOptions}>
        {question.options.map((rule) => {
          const selected = chosen === rule.id;
          const isAnswer = chosen !== null && rule.id === question.answer.id;
          return (
            <button
              key={rule.id}
              type="button"
              disabled={chosen !== null}
              onClick={() => setChosen(rule.id)}
              className={`rounded-xl border-2 p-3 text-left font-semibold disabled:cursor-default ${isAnswer ? "border-emerald-500 bg-emerald-50 text-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-100" : selected ? "border-rose-500 bg-rose-50 text-rose-900 dark:bg-rose-950/40 dark:text-rose-100" : "border-slate-200 bg-white hover:border-brand-500 dark:border-slate-700 dark:bg-slate-900"}`}
            >
              <span lang={language}>{rule.spelling}</span><span className="ml-2 text-sm font-normal text-slate-500">{rule.czech}</span>
            </button>
          );
        })}
      </div>
      {chosen !== null && (
        <div className="flex flex-col gap-2 rounded-xl bg-white p-3 dark:bg-slate-900" aria-live="polite">
          <p className={`flex items-center gap-2 font-semibold ${correct ? "text-emerald-700 dark:text-emerald-300" : "text-rose-700 dark:text-rose-300"}`}>
            {correct ? <CheckCircle2 className="size-4" aria-hidden /> : <XCircle className="size-4" aria-hidden />}
            {correct ? t.quizRight : t.quizReveal(question.answer.spelling, question.answer.czech)}
          </p>
          <p className="text-sm text-slate-600 dark:text-slate-300">{question.answer.note}</p>
          <Button className="self-end" onClick={next}>{t.quizNext}</Button>
        </div>
      )}
      <p className="text-xs text-slate-500">{t.quizNoEvidence}</p>
    </section>
  );
}

function Guide({ language }: { language: Language }) {
  const [rules, setRules] = useState<SoundRule[] | null>(null);
  const [failed, setFailed] = useState(false);
  const [q, setQ] = useState("");

  useEffect(() => {
    let cancelled = false;
    getSounds(language)
      .then((r) => !cancelled && setRules(r))
      .catch(() => !cancelled && setFailed(true));
    return () => {
      cancelled = true;
    };
  }, [language]);

  const shown = useMemo(() => {
    const f = fold(q.trim());
    if (!rules || !f) return rules;
    return rules.filter((r) => fold(r.spelling).includes(f) || fold(r.czech).includes(f) || r.examples.some((e) => fold(e.lemma).includes(f)));
  }, [rules, q]);

  if (failed) return <Notice tone="error">{cs.common.error}</Notice>;
  if (!shown) return <p className="text-sm text-slate-500">{cs.common.loading}</p>;
  return (
    <div className="flex flex-col gap-4">
      <label className="flex max-w-md items-center gap-2 rounded-xl border border-slate-300 bg-white px-3 py-2 dark:border-slate-700 dark:bg-slate-900">
        <Search className="size-4 text-slate-400" aria-hidden />
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder={t.search} aria-label={t.search} className="min-w-0 flex-1 bg-transparent outline-none" />
      </label>
      <div className="grid gap-4 lg:grid-cols-2">
        <div className="lg:col-span-2"><SoundQuiz rules={rules ?? []} language={language} /></div>
        {shown.map((r) => (
          <Rule key={r.id} rule={r} language={language} />
        ))}
      </div>
    </div>
  );
}

export default function SoundsPage() {
  const me = useRequireMe();
  const { state } = useAuth();
  if (state.kind === "error") return <FullPageStatus text={cs.common.offline} />;
  if (!me) return <FullPageStatus text={cs.common.loading} />;
  const language = me.acting.active_language;
  return (
    <AppShell me={me}>
      <div className="flex flex-col gap-2">
        <h1 className="flex items-center gap-2 text-2xl font-bold">
          <AudioLines className="size-6 text-brand-500" aria-hidden /> {t.title}
        </h1>
        <p className="max-w-3xl text-slate-600 dark:text-slate-300">{t.intro}</p>
        <LanguagePicker me={me} />
        <Notice>{t.unreviewed}</Notice>
      </div>
      <Guide key={language} language={language} />
    </AppShell>
  );
}
