"use client";

import { ArrowLeft, BookOpenText, CheckCircle2, Library, XCircle } from "lucide-react";
import { useEffect, useState } from "react";

import { AppShell, FullPageStatus, LanguagePicker } from "@/components/AppShell";
import { Button, Notice } from "@/components/ui";
import { answerLibraryStory, answerLibraryStoryText, getLibraryStory, getProgress, listLibraryStories, type CefrLevel, type LibraryStory, type LibraryStorySummary } from "@/lib/api";
import { useRequireMe } from "@/lib/auth";
import { cs } from "@/lib/i18n/cs";

const LEVELS: CefrLevel[] = ["A1", "A2", "B1", "B2"];

export default function StoryLibraryPage() {
  const me = useRequireMe();
  const language = me?.acting.active_language;
  const [level, setLevel] = useState<CefrLevel>("A1");
  const [stories, setStories] = useState<LibraryStorySummary[]>([]);
  const [story, setStory] = useState<LibraryStory | null>(null);
  const [answers, setAnswers] = useState<Record<number, { correct: boolean; answer: number; choice: number }>>({});
  const [drafts, setDrafts] = useState<Record<number, string>>({});
  const [showTranslation, setShowTranslation] = useState(false);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (!language) return;
    let cancelled = false;
    setFailed(false);
    void Promise.all([getProgress(language), listLibraryStories(language)])
      .then(([progress, library]) => {
        if (cancelled) return;
        const active = LEVELS.includes(progress.cefr_level as CefrLevel) ? progress.cefr_level as CefrLevel : "A1";
        setLevel(active);
        setStories(library);
      })
      .catch(() => !cancelled && setFailed(true));
    return () => { cancelled = true; };
  }, [language]);

  async function open(slug: string) {
    if (!language) return;
    try {
      setStory(await getLibraryStory(language, slug));
      setAnswers({});
      setDrafts({});
      setShowTranslation(false);
    } catch { setFailed(true); }
  }

  async function answer(question: number, choice?: number, text?: string) {
    if (!language || !story || answers[question]) return;
    try {
      const result = text !== undefined
        ? await answerLibraryStoryText(language, story.slug, question, text)
        : await answerLibraryStory(language, story.slug, question, choice!);
      setAnswers((current) => ({ ...current, [question]: { ...result, choice: choice ?? -1 } }));
    } catch { setFailed(true); }
  }

  if (!me) return <FullPageStatus text={cs.common.loading} />;
  const visible = stories.filter((item) => item.level === level);
  return <AppShell me={me}>
    <header className="flex flex-col gap-3">
      <div className="flex items-center gap-2"><BookOpenText className="size-6 text-brand-500" aria-hidden /><h1 className="text-2xl font-bold">{cs.storyLibrary.title}</h1></div>
      <p className="max-w-2xl text-slate-600 dark:text-slate-300">{cs.storyLibrary.intro(stories.length)}</p>
      <LanguagePicker me={me} />
    </header>
    {failed && <Notice tone="error">{cs.storyLibrary.failed}</Notice>}
    {story ? <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_20rem]">
      <article className="flex flex-col gap-4 rounded-3xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <Button variant="ghost" onClick={() => setStory(null)}><ArrowLeft className="size-4" aria-hidden />{cs.storyLibrary.back}</Button>
          <span className="rounded-full bg-brand-500/10 px-3 py-1 text-sm font-semibold">{story.level}</span>
        </div>
        <h2 className="text-2xl font-bold">{story.title}</h2>
        <p className="text-sm text-slate-500">{story.title_cs}</p>
        <ol className="flex flex-col gap-3" lang={language}>
          {story.lines.map((line, index) => <li key={index} className="rounded-xl bg-slate-50 p-3 dark:bg-slate-800/60">
            {line.speaker && <span className="font-semibold">{line.speaker}: </span>}{line.text}
            {showTranslation && <p className="mt-1 text-sm text-slate-500" lang="cs">{line.cs}</p>}
          </li>)}
        </ol>
        <Button variant="secondary" onClick={() => setShowTranslation((v) => !v)}>{showTranslation ? cs.storyLibrary.hideTranslation : cs.storyLibrary.showTranslation}</Button>
        <p className="text-xs text-slate-500">{cs.storyLibrary.unreviewed}</p>
      </article>
      <aside className="flex flex-col gap-3 rounded-3xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
        <h3 className="font-bold">{cs.storyLibrary.questions}</h3>
        {story.questions.map((question, qi) => <fieldset key={qi} className="flex flex-col gap-2 border-b border-slate-200 pb-3 last:border-0 dark:border-slate-800">
          <legend className="mb-2 text-sm font-medium">{question.question}</legend>
          {me.acting.settings.practice_difficulty === "hard" ? <form onSubmit={(event) => { event.preventDefault(); void answer(qi, undefined, drafts[qi] ?? ""); }} className="flex gap-2">
            <input value={drafts[qi] ?? ""} onChange={(event) => setDrafts((current) => ({ ...current, [qi]: event.target.value }))} disabled={!!answers[qi]} className="min-w-0 flex-1 rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-950" aria-label={question.question} />
            <Button type="submit" disabled={!!answers[qi] || !drafts[qi]?.trim()}>{cs.lesson.check}</Button>
          </form> : question.options.map((option, oi) => {
            const result = answers[qi];
            const isCorrect = !!result && oi === result.answer;
            const isWrong = !!result && oi === result.choice && !result.correct;
            return <button key={oi} type="button" disabled={!!result} onClick={() => void answer(qi, oi)} className={`rounded-xl border px-3 py-2 text-left text-sm ${isCorrect ? "border-emerald-500 bg-emerald-50 text-emerald-900" : isWrong ? "border-rose-500 bg-rose-50 text-rose-900" : "border-slate-300 hover:border-brand-500 dark:border-slate-700"}`}>
              <span className="flex items-center gap-2">{isCorrect ? <CheckCircle2 className="size-4" aria-hidden /> : isWrong ? <XCircle className="size-4" aria-hidden /> : null}{option}</span>
            </button>;
          })}
          {answers[qi] && me.acting.settings.practice_difficulty === "hard" && <p role="status" className={`text-sm ${answers[qi]!.correct ? "text-emerald-700" : "text-rose-700"}`}>{answers[qi]!.correct ? cs.stories.right : cs.stories.wrong(question.options[answers[qi]!.answer] ?? "")}</p>}
        </fieldset>)}
        <details><summary className="cursor-pointer text-sm font-semibold">{cs.storyLibrary.stretch}</summary><ul className="mt-2 flex flex-wrap gap-2">{story.stretch.map((word) => <li key={word.word} className="rounded-lg bg-slate-100 px-2 py-1 text-sm dark:bg-slate-800"><b lang={language}>{word.word}</b> · {word.cs}</li>)}</ul></details>
      </aside>
    </div> : <section className="flex flex-col gap-4 rounded-3xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
      <div className="flex items-center gap-3"><label htmlFor="story-level" className="font-semibold">{cs.storyLibrary.level}</label><select id="story-level" value={level} onChange={(event) => setLevel(event.target.value as CefrLevel)} className="rounded-xl border border-slate-300 bg-white px-3 py-2 dark:border-slate-700 dark:bg-slate-950">{LEVELS.map((item) => <option key={item}>{item}</option>)}</select><span className="text-sm text-slate-500">{cs.storyLibrary.count(visible.length)}</span></div>
      {stories.length === 0 && !failed ? <p className="text-sm text-slate-500">{cs.common.loading}</p> : <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">{visible.map((item) => <li key={item.slug}><button type="button" onClick={() => void open(item.slug)} className="flex h-full w-full flex-col gap-2 rounded-2xl border border-slate-200 p-4 text-left hover:border-brand-500 hover:shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 dark:border-slate-800"><span className="flex items-center gap-2 text-xs font-semibold text-brand-600"><Library className="size-4" aria-hidden />{item.level}</span><span className="font-bold">{item.title}</span><span className="text-sm text-slate-500">{item.title_cs}</span><span className="text-xs text-slate-500">{cs.storyLibrary.detail(item.line_count, item.question_count)}</span></button></li>)}</ul>}
    </section>}
  </AppShell>;
}
