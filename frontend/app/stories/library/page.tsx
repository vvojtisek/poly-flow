"use client";

import { ArrowLeft, BookOpenText, Languages, Library, MessagesSquare } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { AppShell, FullPageStatus, LanguagePicker } from "@/components/AppShell";
import { Notice } from "@/components/ui";
import { getLibraryStory, getStoryLibrary, type CefrLevel, type Language, type LibraryStory, type StoryLibrary } from "@/lib/api";
import { useRequireMe } from "@/lib/auth";
import { cs } from "@/lib/i18n/cs";

const t = cs.library;
const LEVELS: CefrLevel[] = ["A1", "A2", "B1", "B2"];

/** One story, read line by line. Ungraded: no questions are scored and nothing is recorded. */
function Reader({ language, slug, onBack }: { language: Language; slug: string; onBack: () => void }) {
  const [story, setStory] = useState<LibraryStory | null>(null);
  const [failed, setFailed] = useState(false);
  const [showCs, setShowCs] = useState(false);
  useEffect(() => {
    let live = true;
    setStory(null);
    setFailed(false);
    getLibraryStory(language, slug)
      .then((s) => live && setStory(s))
      .catch(() => live && setFailed(true));
    return () => {
      live = false;
    };
  }, [language, slug]);

  return (
    <article className="flex flex-col gap-4">
      <button type="button" onClick={onBack} className="inline-flex items-center gap-1 self-start text-sm font-semibold text-brand-700 hover:underline dark:text-brand-200">
        <ArrowLeft className="size-4" aria-hidden /> {t.back}
      </button>
      {failed && <Notice tone="error">{cs.common.error}</Notice>}
      {!story && !failed && <p className="text-sm text-slate-500">{cs.common.loading}</p>}
      {story && (
        <>
          <header>
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              {story.level} · {t.kinds[story.kind]}
            </p>
            <h2 lang={language} className="text-2xl font-bold">{story.title}</h2>
            <p className="text-sm text-slate-500">{story.title_cs}</p>
          </header>
          <button
            type="button"
            onClick={() => setShowCs((v) => !v)}
            aria-pressed={showCs}
            className="inline-flex min-h-11 items-center gap-2 self-start rounded-xl bg-slate-100 px-3 py-2 text-sm font-medium dark:bg-slate-800"
          >
            <Languages className="size-4" aria-hidden /> {showCs ? t.hideCs : t.showCs}
          </button>
          <ol className="flex flex-col gap-3 rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
            {story.lines.map((line, i) => (
              <li key={i} className="flex flex-col gap-0.5">
                {line.speaker && <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">{line.speaker}</span>}
                <span lang={language} className="text-lg leading-relaxed">{line.text}</span>
                {showCs && <span className="text-sm text-slate-500">{line.cs}</span>}
              </li>
            ))}
          </ol>
        </>
      )}
    </article>
  );
}

function Shelf({ library, onOpen }: { library: StoryLibrary; onOpen: (slug: string) => void }) {
  if (!library.stories.length) return <Notice>{t.empty}</Notice>;
  return (
    <div className="flex flex-col gap-5">
      {LEVELS.map((level) => {
        const stories = library.stories.filter((s) => s.level === level);
        if (!stories.length) return null;
        return (
          <section key={level} aria-labelledby={`level-${level}`}>
            <h2 id={`level-${level}`} className="mb-2 text-lg font-bold">{t.level(level, stories.length)}</h2>
            <ul className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {stories.map((s) => (
                <li key={s.slug}>
                  <button
                    type="button"
                    onClick={() => onOpen(s.slug)}
                    aria-label={t.open(s.title)}
                    className="flex h-full w-full flex-col gap-1 rounded-xl border border-slate-200 bg-white p-3 text-left hover:border-brand-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 dark:border-slate-800 dark:bg-slate-900"
                  >
                    <span lang={library.language} className="font-semibold">{s.title}</span>
                    <span className="text-sm text-slate-600 dark:text-slate-300">{s.title_cs}</span>
                    <span className="mt-auto flex items-center gap-1 pt-1 text-xs text-slate-500">
                      {s.kind === "dialogue" ? <MessagesSquare className="size-3.5" aria-hidden /> : <BookOpenText className="size-3.5" aria-hidden />}
                      {t.kinds[s.kind]} · {t.lineCount(s.lines)}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </section>
        );
      })}
    </div>
  );
}

export default function StoryLibraryPage() {
  const me = useRequireMe();
  const language = me?.acting.active_language;
  const [library, setLibrary] = useState<StoryLibrary | null>(null);
  const [failed, setFailed] = useState(false);
  const [slug, setSlugState] = useState<string | null>(null);

  // The open story lives in the URL (?story=slug), so a link, reload or Back reopens it.
  useEffect(() => {
    const wanted = new URLSearchParams(window.location.search).get("story");
    if (wanted && /^[a-z0-9][a-z0-9-]{0,63}$/.test(wanted)) setSlugState(wanted);
  }, []);
  const setSlug = useCallback((value: string | null) => {
    setSlugState(value);
    const q = new URLSearchParams(window.location.search);
    if (value) q.set("story", value);
    else q.delete("story");
    const qs = q.toString();
    window.history.replaceState(window.history.state, "", `${window.location.pathname}${qs ? `?${qs}` : ""}`);
    window.scrollTo({ top: 0 });
  }, []);

  useEffect(() => {
    if (!language) return;
    let live = true;
    setLibrary(null);
    setFailed(false);
    getStoryLibrary(language)
      .then((l) => live && setLibrary(l))
      .catch(() => live && setFailed(true));
    return () => {
      live = false;
    };
  }, [language, me?.acting.id]);

  if (!me || !language) return <FullPageStatus text={cs.common.loading} />;
  return (
    <AppShell me={me}>
      <div className="mx-auto flex w-full max-w-4xl flex-col gap-4">
        <header className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h1 className="flex items-center gap-2 text-2xl font-bold">
              <Library className="size-6 text-brand-500" aria-hidden /> {t.title}
            </h1>
            <p className="mt-1 max-w-2xl text-sm text-slate-600 dark:text-slate-300">{t.intro}</p>
          </div>
          <LanguagePicker me={me} />
        </header>
        {library?.review_status === "unreviewed" && <p className="text-xs text-amber-700 dark:text-amber-300">{t.unreviewed}</p>}
        {failed && <Notice tone="error">{cs.common.error}</Notice>}
        {!library && !failed && <p className="text-sm text-slate-500">{cs.common.loading}</p>}
        {library && (slug ? <Reader key={`${language}:${slug}`} language={language} slug={slug} onBack={() => setSlug(null)} /> : <Shelf library={library} onOpen={setSlug} />)}
        {library && library.source && <p className="text-xs text-slate-500">{t.provenance(library.source, library.license)}</p>}
        <Link href="/stories" className="self-start text-sm font-medium text-brand-700 hover:underline dark:text-brand-200">
          {cs.stories.title}
        </Link>
      </div>
    </AppShell>
  );
}
