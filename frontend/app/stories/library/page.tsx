"use client";

import { ArrowLeft, BookOpenText, Languages, Library, MessagesSquare, Play, Square } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

import { AppShell, FullPageStatus, LanguagePicker } from "@/components/AppShell";
import { PlayButton, SlowToggle } from "@/components/PlayButton";
import { Notice } from "@/components/ui";
import { clipSrc, playToEnd, stop } from "@/lib/audio";
import { getLibraryStory, getStoryLibrary, libraryAudioUrl, type CefrLevel, type Language, type LibraryStory, type StoryLibrary } from "@/lib/api";
import { useRequireMe } from "@/lib/auth";
import { cs } from "@/lib/i18n/cs";

const t = cs.library;
const LEVELS: CefrLevel[] = ["A1", "A2", "B1", "B2"];

type Gloss = { word: string; cs: string };

/** Splits a line at the story's stretch words (whole words, any case, longest form first). */
function glossParts(text: string, stretch: Gloss[]): (string | Gloss)[] {
  if (!stretch.length) return [text];
  const forms = [...stretch].sort((a, b) => b.word.length - a.word.length);
  const escaped = forms.map((g) => g.word.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
  const rx = new RegExp(`(?<![\\p{L}\\p{N}])(${escaped.join("|")})(?![\\p{L}\\p{N}])`, "giu");
  const out: (string | Gloss)[] = [];
  let last = 0;
  for (const m of text.matchAll(rx)) {
    const at = m.index ?? 0;
    if (at > last) out.push(text.slice(last, at));
    const hit = forms.find((g) => g.word.toLocaleLowerCase() === m[0].toLocaleLowerCase());
    out.push(hit ? { word: m[0], cs: hit.cs } : m[0]);
    last = at + m[0].length;
  }
  if (last < text.length) out.push(text.slice(last));
  return out;
}

/** A line with its stretch words marked; tapping one shows its Czech gloss in place. */
function GlossedLine({ text, stretch, language }: { text: string; stretch: Gloss[]; language: Language }) {
  const [open, setOpen] = useState<number | null>(null);
  return (
    <span lang={language} className="text-lg leading-relaxed">
      {glossParts(text, stretch).map((part, i) =>
        typeof part === "string" ? (
          <span key={i}>{part}</span>
        ) : (
          <span key={i} className="inline">
            <button
              type="button"
              onClick={() => setOpen((v) => (v === i ? null : i))}
              aria-expanded={open === i}
              aria-label={t.glossFor(part.word)}
              className="rounded underline decoration-amber-500 decoration-dotted decoration-2 underline-offset-4 hover:bg-amber-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 dark:hover:bg-amber-500/20"
            >
              {part.word}
            </button>
            {open === i && (
              <span lang="cs" className="ml-1 rounded bg-amber-100 px-1.5 py-0.5 text-sm text-amber-900 dark:bg-amber-500/20 dark:text-amber-100">
                {part.cs}
              </span>
            )}
          </span>
        ),
      )}
    </span>
  );
}

/** One story, read line by line. Ungraded: no questions are scored and nothing is recorded. */
function Reader({ language, slug, onBack }: { language: Language; slug: string; onBack: () => void }) {
  const [story, setStory] = useState<LibraryStory | null>(null);
  const [failed, setFailed] = useState(false);
  const [showCs, setShowCs] = useState(false);
  // Reading aloud: every line in turn, the current one highlighted. null = not reading.
  const [reading, setReading] = useState<number | null>(null);
  const [noAudio, setNoAudio] = useState(false);
  const run = useRef(0);
  const readFrom = useCallback(
    async (start: number) => {
      if (!story) return;
      const me = ++run.current;
      setNoAudio(false);
      for (let i = start; i < story.lines.length; i++) {
        if (me !== run.current) return;
        const url = libraryAudioUrl(language, slug, i);
        try {
          await clipSrc(url); // fails fast when speech is unavailable, instead of skipping lines
        } catch {
          if (me === run.current) {
            setNoAudio(true);
            setReading(null);
          }
          return;
        }
        if (me !== run.current) return;
        setReading(i);
        document.querySelector(`[data-line="${i}"]`)?.scrollIntoView({ block: "nearest", behavior: "smooth" });
        await playToEnd(url);
      }
      if (me === run.current) setReading(null);
    },
    [story, language, slug],
  );
  const stopReading = useCallback(() => {
    run.current += 1;
    stop();
    setReading(null);
  }, []);
  // Leaving the story stops its voice.
  useEffect(() => () => {
    run.current += 1;
    stop();
  }, []);
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
          <div className="flex flex-wrap items-center gap-2">
            {reading === null ? (
              <button type="button" onClick={() => void readFrom(0)} className="inline-flex min-h-11 items-center gap-2 rounded-xl bg-brand-500 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-600">
                <Play className="size-4" aria-hidden /> {t.readAloud}
              </button>
            ) : (
              <button type="button" onClick={stopReading} className="inline-flex min-h-11 items-center gap-2 rounded-xl bg-rose-600 px-4 py-2 text-sm font-semibold text-white">
                <Square className="size-4" aria-hidden /> {t.stopReading}
              </button>
            )}
            <button
              type="button"
              onClick={() => setShowCs((v) => !v)}
              aria-pressed={showCs}
              className="inline-flex min-h-11 items-center gap-2 rounded-xl bg-slate-100 px-3 py-2 text-sm font-medium dark:bg-slate-800"
            >
              <Languages className="size-4" aria-hidden /> {showCs ? t.hideCs : t.showCs}
            </button>
            <SlowToggle />
          </div>
          {noAudio && <Notice>{t.noAudio}</Notice>}
          {/* Context first: the few above-level words, with glosses, before the text itself. */}
          {story.stretch.length > 0 && (
            <section aria-labelledby="stretch-title" className="rounded-2xl bg-amber-50 p-3 text-sm dark:bg-amber-950/30">
              <h3 id="stretch-title" className="font-semibold">{t.stretchTitle}</h3>
              <p className="text-xs text-slate-600 dark:text-slate-300">{t.stretchHelp}</p>
              <ul className="mt-2 flex flex-wrap gap-x-4 gap-y-1">
                {story.stretch.map((w) => (
                  <li key={w.word}>
                    <strong lang={language}>{w.word}</strong> = {w.cs}
                  </li>
                ))}
              </ul>
            </section>
          )}
          <ol className="flex flex-col gap-3 rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
            {story.lines.map((line, i) => (
              <li
                key={i}
                data-line={i}
                aria-current={reading === i ? "true" : undefined}
                className={`flex items-start gap-2 rounded-xl px-2 py-1 transition-colors ${reading === i ? "bg-brand-500/10" : ""}`}
              >
                <PlayButton url={libraryAudioUrl(language, slug, i)} size="sm" label={t.playLine(i + 1)} />
                <span className="flex min-w-0 flex-col gap-0.5">
                  {line.speaker && <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">{line.speaker}</span>}
                  <GlossedLine text={line.text} stretch={story.stretch} language={language} />
                  {showCs && <span className="text-sm text-slate-500">{line.cs}</span>}
                </span>
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
