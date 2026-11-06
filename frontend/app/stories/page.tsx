"use client";

import { BookOpenText, CheckCircle2, Languages, MessagesSquare, XCircle } from "lucide-react";
import { useEffect, useState } from "react";

import { AppShell, FullPageStatus, LanguagePicker } from "@/components/AppShell";
import { PlayButton } from "@/components/PlayButton";
import { Button, Notice } from "@/components/ui";
import {
  ApiError,
  answerStoryQuestion,
  generateStory,
  getStoryToday,
  storyAudioUrl,
  type Language,
  type Story,
} from "@/lib/api";
import { useRequireMe } from "@/lib/auth";
import { cs } from "@/lib/i18n/cs";

type Result = { choice: number; correct: boolean; answer: number };

const ERRORS: Record<string, string> = {
  model_unavailable: cs.stories.unavailable,
  not_enough_words: cs.stories.notEnoughWords,
  story_generating: cs.stories.generating,
  story_failed: cs.stories.failed,
};

function Reader({ story }: { story: Story }) {
  const [translate, setTranslate] = useState(false);
  const [results, setResults] = useState<Record<number, Result>>({});
  const [busy, setBusy] = useState(false);

  async function answer(index: number, choice: number) {
    setBusy(true);
    try {
      const r = await answerStoryQuestion(story.id, index, choice);
      setResults((prev) => ({ ...prev, [index]: { choice, correct: r.correct, answer: r.answer_index } }));
    } finally {
      setBusy(false);
    }
  }

  const allAnswered = story.questions.every((q, i) => results[i] || q.answered !== null);
  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
      <article className="flex flex-col gap-3 rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="flex items-center gap-2 text-xl font-bold" lang={story.language}>
            {story.kind === "dialogue" ? (
              <MessagesSquare className="size-5 text-brand-500" aria-hidden />
            ) : (
              <BookOpenText className="size-5 text-brand-500" aria-hidden />
            )}
            {story.title}
          </h2>
          <Button variant="ghost" className="text-sm" onClick={() => setTranslate((t) => !t)} aria-pressed={translate}>
            <Languages className="size-4" aria-hidden /> {translate ? cs.stories.hideTranslation : cs.stories.showTranslation}
          </Button>
        </div>
        <ol className="flex flex-col gap-3">
          {story.lines.map((ln, i) => (
            <li key={i} className="flex items-start gap-2">
              <PlayButton url={storyAudioUrl(story.id, i)} label={cs.stories.playLine} size="sm" />
              <div className="flex flex-col">
                <p className="text-lg" lang={story.language}>
                  {ln.speaker && <span className="font-semibold">{ln.speaker}: </span>}
                  {ln.text}
                </p>
                {translate && (
                  <p className="text-sm text-slate-500" lang="cs">
                    {ln.cs}
                  </p>
                )}
              </div>
            </li>
          ))}
        </ol>
        <p className="text-xs text-slate-500">{cs.stories.unreviewed(story.model)}</p>
      </article>

      <aside className="flex flex-col gap-4">
        <section className="flex flex-col gap-2 rounded-2xl border border-slate-200 bg-white p-4 text-sm dark:border-slate-800 dark:bg-slate-900">
          <p className="font-semibold">{cs.stories.targets}</p>
          <ul className="flex flex-wrap gap-1" lang={story.language}>
            {story.targets.map((t) => (
              <li key={t} className="rounded-lg bg-brand-50 px-2 py-1 text-brand-900 dark:bg-slate-800 dark:text-slate-100">
                {t}
              </li>
            ))}
          </ul>
          {story.glossary.length > 0 && (
            <>
              <p className="mt-2 font-semibold">{cs.stories.glossary}</p>
              <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1">
                {story.glossary.map((g) => (
                  <div key={g.word} className="contents">
                    <dt lang={story.language} className="font-medium">
                      {g.word}
                    </dt>
                    <dd className="text-slate-600 dark:text-slate-300">{g.cs}</dd>
                  </div>
                ))}
              </dl>
            </>
          )}
        </section>

        <section className="flex flex-col gap-3 rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
          <h3 className="font-semibold">{cs.stories.questions}</h3>
          {story.questions.map((q, i) => {
            const r = results[i];
            return (
              <fieldset key={i} className="flex flex-col gap-2">
                <legend className="mb-1 text-sm font-medium">
                  {i + 1}. {q.question}
                </legend>
                <div className="flex flex-wrap gap-2">
                  {q.options.map((o, j) => {
                    const state = !r ? "" : j === r.answer ? "correct" : j === r.choice ? "wrong" : "";
                    return (
                      <button
                        key={j}
                        type="button"
                        disabled={busy || !!r}
                        onClick={() => void answer(i, j)}
                        className={`rounded-xl border px-3 py-2 text-sm font-medium transition disabled:cursor-default ${
                          state === "correct"
                            ? "border-emerald-500 bg-emerald-50 text-emerald-900 dark:bg-emerald-950 dark:text-emerald-100"
                            : state === "wrong"
                              ? "border-rose-500 bg-rose-50 text-rose-900 dark:bg-rose-950 dark:text-rose-100"
                              : "border-slate-300 hover:bg-slate-50 dark:border-slate-700 dark:hover:bg-slate-800"
                        }`}
                      >
                        {o}
                      </button>
                    );
                  })}
                </div>
                {r && (
                  <p className="flex items-center gap-1 text-sm" role="status">
                    {r.correct ? (
                      <>
                        <CheckCircle2 className="size-4 text-emerald-600" aria-hidden /> {cs.stories.right}
                      </>
                    ) : (
                      <>
                        <XCircle className="size-4 text-rose-600" aria-hidden /> {cs.stories.wrong(q.options[r.answer] ?? "")}
                      </>
                    )}
                  </p>
                )}
              </fieldset>
            );
          })}
          {allAnswered && <Notice tone="ok">{cs.stories.done}</Notice>}
        </section>
      </aside>
    </div>
  );
}

export default function StoriesPage() {
  const me = useRequireMe();
  const language = me?.acting.active_language as Language | undefined;
  const [state, setState] = useState<{ available: boolean; story: Story | null } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [writing, setWriting] = useState(false);

  useEffect(() => {
    if (!language) return;
    let cancelled = false;
    setState(null);
    setError(null);
    getStoryToday(language)
      .then((t) => !cancelled && setState({ available: t.model_available, story: t.story }))
      .catch(() => !cancelled && setError(cs.common.error));
    return () => {
      cancelled = true;
    };
  }, [language, me?.acting.id]);

  async function write(kind: Story["kind"]) {
    if (!language) return;
    setWriting(true);
    setError(null);
    try {
      const story = await generateStory(language, kind);
      setState({ available: true, story });
    } catch (e) {
      setError(e instanceof ApiError ? (ERRORS[e.code] ?? cs.common.error) : cs.common.offline);
    } finally {
      setWriting(false);
    }
  }

  if (!me) return <FullPageStatus text={cs.common.loading} />;
  return (
    <AppShell me={me}>
      <div className="flex flex-col gap-4">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div className="flex flex-col gap-1">
            <h1 className="flex items-center gap-2 text-2xl font-bold">
              <BookOpenText className="size-6 text-brand-500" aria-hidden /> {cs.stories.title}
            </h1>
            <p className="max-w-2xl text-sm text-slate-600 dark:text-slate-300">{cs.stories.intro}</p>
          </div>
          <LanguagePicker me={me} />
        </div>
        {!state && !error && <p className="text-slate-500">{cs.common.loading}</p>}
        {error && <Notice tone="error">{error}</Notice>}
        {state && !state.available && !state.story && (
          <Notice>{me.acting.is_child ? cs.stories.childUnavailable : cs.stories.unavailable}</Notice>
        )}
        {state && state.available && !state.story && (
          <div className="flex flex-col gap-2 sm:flex-row">
            <Button disabled={writing} onClick={() => void write("story")}>
              <BookOpenText className="size-5" aria-hidden /> {cs.stories.story}
            </Button>
            <Button variant="secondary" disabled={writing} onClick={() => void write("dialogue")}>
              <MessagesSquare className="size-5" aria-hidden /> {cs.stories.dialogue}
            </Button>
          </div>
        )}
        {writing && <p className="text-slate-500" role="status">{cs.stories.writing}</p>}
        {state?.story && <Reader story={state.story} />}
      </div>
    </AppShell>
  );
}
