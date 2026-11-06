"use client";

import { BookOpenText, CheckCircle2, Languages, MessagesSquare, Play, Square, Trash2, XCircle } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { AppShell, FullPageStatus, LanguagePicker } from "@/components/AppShell";
import { PlayButton } from "@/components/PlayButton";
import { TapText } from "@/components/TapText";
import { Button, Notice } from "@/components/ui";
import {
  ApiError,
  answerStoryQuestion,
  deleteStory,
  generateStory,
  getStory,
  getStoryToday,
  listWordCollections,
  listStoryArchive,
  storyAudioUrl,
  type Language,
  type Story,
  type StoryArchiveItem,
  type WordCollection,
} from "@/lib/api";
import { useRequireMe } from "@/lib/auth";
import { cs } from "@/lib/i18n/cs";

type Result = { choice: number; correct: boolean; answer: number };

const ERRORS: Record<string, string> = {
  model_unavailable: cs.stories.unavailable,
  not_enough_words: cs.stories.notEnoughWords,
  collection_too_small: cs.stories.collectionTooSmall,
  story_generating: cs.stories.generating,
  story_failed: cs.stories.failed,
};

function Reader({ story }: { story: Story }) {
  const [translate, setTranslate] = useState(false);
  const [results, setResults] = useState<Record<number, Result>>({});
  const [busy, setBusy] = useState(false);
  const [answerError, setAnswerError] = useState<{ index: number; choice: number } | null>(null);
  const [activeLine, setActiveLine] = useState<number | null>(null);
  const [audioError, setAudioError] = useState(false);
  const audio = useRef<HTMLAudioElement>(null);
  const answerVersion = useRef(0);

  useEffect(() => {
    if (activeLine === null || !audio.current) return;
    audio.current.currentTime = 0;
    void audio.current.play().catch(() => setAudioError(true));
  }, [activeLine]);

  useEffect(() => {
    answerVersion.current += 1;
    setResults({});
    setAnswerError(null);
    setBusy(false);
    setActiveLine(null);
    setAudioError(false);
  }, [story.id]);

  function listenFrom(index: number) {
    setAudioError(false);
    if (activeLine !== index) setActiveLine(index);
    else if (audio.current) {
      audio.current.currentTime = 0;
      void audio.current.play().catch(() => setAudioError(true));
    }
  }

  function lineEnded() {
    setActiveLine((line) => line !== null && line + 1 < story.lines.length ? line + 1 : null);
  }

  async function answer(index: number, choice: number) {
    const version = answerVersion.current;
    setBusy(true);
    setAnswerError(null);
    try {
      const r = await answerStoryQuestion(story.id, index, choice);
      if (answerVersion.current === version) {
        setResults((prev) => ({ ...prev, [index]: { choice, correct: r.correct, answer: r.answer_index } }));
      }
    } catch {
      if (answerVersion.current === version) setAnswerError({ index, choice });
    } finally {
      if (answerVersion.current === version) setBusy(false);
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
        <div className="flex flex-wrap items-center gap-2 rounded-xl bg-slate-50 p-3 dark:bg-slate-800/60">
          <Button variant="secondary" onClick={() => listenFrom(0)} disabled={story.lines.length === 0}>
            <Play className="size-4" aria-hidden /> {cs.stories.listenAll}
          </Button>
          {activeLine !== null && (
            <>
              <audio
                ref={audio}
                controls
                preload="none"
                src={storyAudioUrl(story.id, activeLine)}
                onEnded={lineEnded}
                onError={() => setAudioError(true)}
                aria-label={cs.stories.listenAll}
                className="h-10 min-w-48 flex-1"
              />
              <Button variant="ghost" onClick={() => setActiveLine(null)}>
                <Square className="size-4" aria-hidden /> {cs.stories.stopReading}
              </Button>
            </>
          )}
          {audioError && <p className="w-full text-sm text-rose-700 dark:text-rose-300" role="alert">{cs.stories.audioFailed}</p>}
          {activeLine !== null && <span className="sr-only">{cs.stories.linePosition(activeLine + 1, story.lines.length)}</span>}
        </div>
        <ol className="flex flex-col gap-3">
          {story.lines.map((ln, i) => (
            <li key={i} aria-current={activeLine === i ? "true" : undefined} className={`flex items-start gap-2 rounded-xl p-2 transition-colors ${activeLine === i ? "bg-brand-500/10 ring-1 ring-brand-500/40" : ""}`}>
              <button type="button" onClick={() => listenFrom(i)} aria-label={cs.stories.listenFromLine(i + 1)} title={cs.stories.listenFromLine(i + 1)} className="mt-1 rounded-full p-2 text-brand-600 hover:bg-brand-500/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 dark:text-brand-200">
                <Play className="size-4" aria-hidden />
              </button>
              <PlayButton url={storyAudioUrl(story.id, i)} label={cs.stories.playLine} size="sm" />
              <div className="flex flex-col">
                <p className="text-lg" lang={story.language}>
                  {ln.speaker && <span className="font-semibold">{ln.speaker}: </span>}
                  <TapText text={ln.text} language={story.language} />
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
        <p className="text-xs text-slate-500">
          {cs.lookup.hint} {cs.stories.unreviewed(story.model)}
        </p>
      </article>

      <aside className="flex flex-col gap-4">
        <section className="flex flex-col gap-2 rounded-2xl border border-slate-200 bg-white p-4 text-sm dark:border-slate-800 dark:bg-slate-900">
          <p className="font-semibold">{cs.stories.targets}</p>
          {story.source_collection && <p className="rounded-lg bg-brand-500/10 px-2 py-1 text-brand-700 dark:text-brand-100">{cs.stories.fromCollection(story.source_collection)}</p>}
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
                        disabled={busy || !!r || q.answered !== null || answerError?.index === i}
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
          {answerError && (
            <div className="flex flex-wrap items-center gap-2" role="alert">
              <p className="text-sm text-rose-700 dark:text-rose-300">{cs.stories.answerFailed}</p>
              <Button variant="secondary" disabled={busy} onClick={() => void answer(answerError.index, answerError.choice)}>{cs.stories.retryAnswer}</Button>
            </div>
          )}
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
  const [collections, setCollections] = useState<WordCollection[]>([]);
  const [collectionId, setCollectionId] = useState("");
  const [collectionsFailed, setCollectionsFailed] = useState(false);
  const [archive, setArchive] = useState<StoryArchiveItem[]>([]);
  const [archiveFailed, setArchiveFailed] = useState(false);
  const [archiveLoading, setArchiveLoading] = useState("");
  const [archivedStory, setArchivedStory] = useState<Story | null>(null);

  useEffect(() => {
    if (!language) return;
    let cancelled = false;
    setState(null);
    setError(null);
    setArchivedStory(null);
    getStoryToday(language)
      .then((t) => !cancelled && setState({ available: t.model_available, story: t.story }))
      .catch(() => !cancelled && setError(cs.common.error));
    return () => {
      cancelled = true;
    };
  }, [language, me?.acting.id]);

  useEffect(() => {
    if (!language) return;
    let cancelled = false;
    setArchive([]);
    setArchiveFailed(false);
    listStoryArchive(language)
      .then((items) => !cancelled && setArchive(items))
      .catch(() => !cancelled && setArchiveFailed(true));
    return () => { cancelled = true; };
  }, [language, me?.acting.id]);

  useEffect(() => {
    if (!language) return;
    let cancelled = false;
    setCollections([]);
    setCollectionId("");
    setCollectionsFailed(false);
    listWordCollections(language)
      .then((items) => !cancelled && setCollections(items))
      .catch(() => !cancelled && setCollectionsFailed(true));
    return () => { cancelled = true; };
  }, [language, me?.acting.id]);

  async function write(kind: Story["kind"]) {
    if (!language) return;
    setWriting(true);
    setError(null);
    try {
      const story = await generateStory(language, kind, collectionId || undefined);
      setArchivedStory(null);
      setState({ available: true, story });
      try {
        setArchive(await listStoryArchive(language));
        setArchiveFailed(false);
      } catch {
        setArchiveFailed(true);
      }
    } catch (e) {
      setError(e instanceof ApiError ? (ERRORS[e.code] ?? cs.common.error) : cs.common.offline);
    } finally {
      setWriting(false);
    }
  }

  async function openArchive(id: string) {
    setArchiveLoading(id);
    try {
      setArchivedStory(await getStory(id));
    } catch {
      setArchiveFailed(true);
    } finally {
      setArchiveLoading("");
    }
  }

  async function removeArchiveStory(item: StoryArchiveItem) {
    if (!window.confirm(cs.stories.deleteConfirm(item.title))) return;
    setArchiveLoading(item.id);
    try {
      await deleteStory(item.id);
      setArchive((items) => items.filter((entry) => entry.id !== item.id));
      setArchivedStory((story) => story?.id === item.id ? null : story);
      setState((current) => current?.story?.id === item.id ? { ...current, story: null } : current);
      setArchiveFailed(false);
    } catch {
      setArchiveFailed(true);
    } finally {
      setArchiveLoading("");
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
        {state && !state.available && !state.story && !archivedStory && (
          <Notice>{me.acting.is_child ? cs.stories.childUnavailable : cs.stories.unavailable}</Notice>
        )}
        {archiveFailed && archive.length === 0 && <Notice tone="error">{cs.stories.archiveFailed}</Notice>}
        {archive.length > 0 && (
          <section className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
            <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
              <h2 className="font-bold">{cs.stories.archiveTitle}</h2>
              {archivedStory && state?.story && <Button variant="ghost" onClick={() => setArchivedStory(null)}>{cs.stories.backToToday}</Button>}
            </div>
            {archiveFailed && <Notice tone="error">{cs.stories.archiveFailed}</Notice>}
            <ul className="flex max-h-56 flex-col gap-2 overflow-y-auto">
              {archive.map((item) => (
                <li key={item.id} className="flex items-center gap-2">
                  <button type="button" aria-pressed={(archivedStory?.id ?? state?.story?.id) === item.id} disabled={archiveLoading !== ""} onClick={() => void openArchive(item.id)} className={`flex min-w-0 flex-1 items-center justify-between gap-3 rounded-xl border px-3 py-2 text-left ${((archivedStory?.id ?? state?.story?.id) === item.id) ? "border-brand-500 bg-brand-500/10" : "border-slate-200 hover:border-brand-500 dark:border-slate-800"}`}>
                    <span className="min-w-0"><span className="block text-xs text-slate-500">{new Date(`${item.story_date}T12:00:00`).toLocaleDateString("cs-CZ", { day: "numeric", month: "long", year: "numeric" })}</span><span className="block truncate font-semibold">{item.title}</span></span>
                    <span className="shrink-0 text-xs text-slate-500">{item.kind === "dialogue" ? cs.stories.dialogue : cs.stories.story}</span>
                  </button>
                  <Button variant="ghost" disabled={archiveLoading !== ""} onClick={() => void removeArchiveStory(item)} aria-label={cs.stories.deleteEntry(item.title)} className="shrink-0 text-rose-700 dark:text-rose-300">
                    <Trash2 className="size-4" aria-hidden />
                  </Button>
                </li>
              ))}
            </ul>
          </section>
        )}
        {state && state.available && !state.story && !archivedStory && (
          <div className="flex flex-col gap-3 rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
            {collections.length > 0 && (
              <label className="flex max-w-xl flex-col gap-1 text-sm font-medium">
                {cs.stories.sourceCollection}
                <select value={collectionId} onChange={(event) => setCollectionId(event.target.value)} disabled={writing} className="rounded-xl border border-slate-300 bg-white px-3 py-2 dark:border-slate-700 dark:bg-slate-900">
                  <option value="">{cs.stories.fromLearningPlan}</option>
                  {collections.map((collection) => (
                    <option key={collection.id} value={collection.id} disabled={collection.count < 3}>
                      {collection.name} · {cs.collections.count(collection.count)}{collection.count < 3 ? ` · ${cs.stories.collectionNeedsMore}` : ""}
                    </option>
                  ))}
                </select>
                <span className="text-xs font-normal text-slate-500">{cs.stories.collectionHelp}</span>
              </label>
            )}
            {collectionsFailed && <Notice>{cs.stories.collectionsUnavailable}</Notice>}
            <div className="flex flex-col gap-2 sm:flex-row">
              <Button disabled={writing} onClick={() => void write("story")}>
                <BookOpenText className="size-5" aria-hidden /> {cs.stories.story}
              </Button>
              <Button variant="secondary" disabled={writing} onClick={() => void write("dialogue")}>
                <MessagesSquare className="size-5" aria-hidden /> {cs.stories.dialogue}
              </Button>
            </div>
          </div>
        )}
        {writing && <p className="text-slate-500" role="status">{cs.stories.writing}</p>}
        {(archivedStory || state?.story) && <Reader story={archivedStory ?? state!.story!} />}
      </div>
    </AppShell>
  );
}
