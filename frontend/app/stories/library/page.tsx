"use client";

import { ArrowLeft, BookOpenText, ChevronLeft, ChevronRight, Waves, CheckCircle2, XCircle, Languages, Library, MessagesSquare, Play, Square } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

import { AppShell, FullPageStatus, LanguagePicker } from "@/components/AppShell";
import { Kbd } from "@/components/Kbd";
import { PlayButton, SlowToggle } from "@/components/PlayButton";
import { isTypingTarget } from "@/lib/keyboard";
import { Notice, RetryNotice, Skeleton } from "@/components/ui";
import { clipSrc, playToEnd, stop } from "@/lib/audio";
import { ApiError, answerLibraryQuestion, getDiagnosticInfo, getLibraryStory, getProgress, getStoryLibrary, libraryAudioUrl, type CefrLevel, type Language, type LibraryStory, type StoryLibrary } from "@/lib/api";
import { useRequireMe } from "@/lib/auth";
import { cs } from "@/lib/i18n/cs";
import { fold } from "@/lib/palette";

const t = cs.library;
const LEVELS: CefrLevel[] = ["A1", "A2", "B1", "B2"];
/** Reading level for an estimate: the estimated level itself (texts are ~95% of their level). */
const READ_AT: Record<string, CefrLevel> = { "pre-A1": "A1", A1: "A1", A2: "A2", B1: "B1", B2: "B2", "B2+": "B2", C1: "B2", C2: "B2" };

type Filters = { q: string; level: CefrLevel | null; kind: "story" | "dialogue" | null; unread: boolean };
const NO_FILTERS: Filters = { q: "", level: null, kind: null, unread: false };
const searchable = (text: string) => fold(text).replace(/ß/g, "ss");

function readFilters(): Filters {
  const q = new URLSearchParams(window.location.search);
  const level = q.get("level");
  const kind = q.get("kind");
  return {
    q: (q.get("q") ?? "").slice(0, 80),
    level: level && (LEVELS as string[]).includes(level) ? (level as CefrLevel) : null,
    kind: kind === "story" || kind === "dialogue" ? kind : null,
    unread: q.get("unread") === "1",
  };
}

function writeFilters(f: Filters) {
  const q = new URLSearchParams(window.location.search);
  for (const k of ["q", "level", "kind", "unread"]) q.delete(k);
  if (f.q.trim()) q.set("q", f.q.trim());
  if (f.level) q.set("level", f.level);
  if (f.kind) q.set("kind", f.kind);
  if (f.unread) q.set("unread", "1");
  const qs = q.toString();
  window.history.replaceState(window.history.state, "", `${window.location.pathname}${qs ? `?${qs}` : ""}`);
}

function applyFilters(stories: StoryLibrary["stories"], f: Filters, read: Set<string>) {
  const needle = searchable(f.q.trim());
  return stories.filter(
    (s) =>
      (!f.level || s.level === f.level) &&
      (!f.kind || s.kind === f.kind) &&
      (!f.unread || !read.has(s.slug)) &&
      (!needle || searchable(`${s.title} ${s.title_cs}`).includes(needle)),
  );
}

function FilterBar({ filters, onChange, shown, total }: { filters: Filters; onChange: (f: Filters) => void; shown: number; total: number }) {
  const chip = (active: boolean) =>
    `shrink-0 rounded-full px-3 py-1 text-sm font-medium ${active ? "bg-brand-500 text-white" : "bg-slate-100 dark:bg-slate-800"}`;
  return (
    <div className="flex flex-col gap-2">
      <input
        type="search"
        data-page-search
        value={filters.q}
        onChange={(e) => onChange({ ...filters, q: e.target.value })}
        placeholder={t.searchPlaceholder}
        aria-label={t.searchLabel}
        className="min-h-11 w-full rounded-xl border border-slate-300 bg-white px-3 dark:border-slate-700 dark:bg-slate-900"
      />
      <div role="radiogroup" aria-label={t.levelFilter} className="-mx-1 flex gap-1 overflow-x-auto px-1 [scrollbar-width:none]">
        {[null, ...LEVELS].map((level) => (
          <button key={level ?? "all"} type="button" role="radio" aria-checked={filters.level === level} onClick={() => onChange({ ...filters, level })} className={chip(filters.level === level)}>
            {level ?? t.allLevels}
          </button>
        ))}
      </div>
      <div className="flex flex-wrap items-center gap-1">
        <div role="radiogroup" aria-label={t.kindFilter} className="flex gap-1">
          {([null, "story", "dialogue"] as const).map((kind) => (
            <button key={kind ?? "all"} type="button" role="radio" aria-checked={filters.kind === kind} onClick={() => onChange({ ...filters, kind })} className={chip(filters.kind === kind)}>
              {kind ? t.kindsPlural[kind] : t.allKinds}
            </button>
          ))}
        </div>
        <label className="ml-auto flex min-h-11 items-center gap-2 text-sm">
          <input type="checkbox" checked={filters.unread} onChange={(e) => onChange({ ...filters, unread: e.target.checked })} className="size-4 accent-brand-500" />
          {t.unreadOnly}
        </label>
      </div>
      <p className="text-xs text-slate-500" aria-live="polite">{t.shown(shown, total)}</p>
    </div>
  );
}

/**
 * Stories this profile has finished on this device (all questions answered, or marked done).
 * A per-device convenience keyed by profile and language: it is not learning evidence.
 */
function useReadMarks(profileId: string | undefined, language: Language | undefined) {
  const key = profileId && language ? `polyflow.library.read.${profileId}.${language}` : null;
  const [read, setRead] = useState<Set<string>>(new Set());
  useEffect(() => {
    if (!key) return;
    try {
      setRead(new Set(JSON.parse(window.localStorage.getItem(key) ?? "[]") as string[]));
    } catch {
      setRead(new Set());
    }
  }, [key]);
  const mark = useCallback(
    (slug: string) => {
      setRead((prev) => {
        if (prev.has(slug)) return prev;
        const next = new Set(prev).add(slug);
        try {
          if (key) window.localStorage.setItem(key, JSON.stringify([...next]));
        } catch {
          /* storage blocked: the mark lasts for this visit */
        }
        return next;
      });
    },
    [key],
  );
  return [read, mark] as const;
}

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
    <span lang={language} className="leading-relaxed">
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

/**
 * Comprehension questions after reading: a check of understanding, not a test. Wrong picks can be
 * retried (learning mode), the answer can be shown, and nothing is stored or counted.
 */
type QState = { wrong: number[]; right: number | null; typedMisses: number };
const NO_ANSWER: QState = { wrong: [], right: null, typedMisses: 0 };

/** Comprehension check. Under the "hard" practice difficulty the learner types the answer instead
 *  of picking it; either way it is checked on the server and nothing is recorded. */
function Questions({ language, slug, questions, onAllDone, typed }: { language: Language; slug: string; questions: { question: string; options: string[] }[]; onAllDone: () => void; typed: boolean }) {
  const [state, setState] = useState<Record<number, QState>>({});
  const [drafts, setDrafts] = useState<Record<number, string>>({});
  const [busy, setBusy] = useState<number | null>(null);
  const [failed, setFailed] = useState(false);
  async function pick(q: number, answer: { choice: number } | { text: string }, reveal = false) {
    setBusy(q);
    setFailed(false);
    try {
      const r = await answerLibraryQuestion(language, slug, q, answer);
      setState((s) => {
        const cur = s[q] ?? NO_ANSWER;
        if (reveal || r.correct) return { ...s, [q]: { ...cur, right: r.answer_index } };
        if ("text" in answer) return { ...s, [q]: { ...cur, typedMisses: cur.typedMisses + 1 } };
        return { ...s, [q]: { ...cur, wrong: [...cur.wrong, answer.choice] } };
      });
    } catch {
      setFailed(true);
    } finally {
      setBusy(null);
    }
  }
  const allDone = questions.length > 0 && questions.every((_, i) => state[i]?.right != null);
  useEffect(() => {
    if (allDone) onAllDone();
  }, [allDone, onAllDone]);
  if (!questions.length) return null;
  return (
    <section aria-labelledby="questions-title" className="flex flex-col gap-3 rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
      <div>
        <h3 id="questions-title" className="text-lg font-bold">{t.questionsTitle}</h3>
        <p className="text-xs text-slate-500">{t.questionsHelp}</p>
        {typed && <p className="text-xs text-slate-500">{t.typedHelp}</p>}
      </div>
      {questions.map((q, qi) => {
        const st = state[qi] ?? NO_ANSWER;
        const done = st.right !== null;
        if (typed) {
          const draft = drafts[qi] ?? "";
          return (
            <fieldset key={qi} className="flex flex-col gap-2">
              <legend lang={language} className="mb-1 font-medium">{q.question}</legend>
              <form
                className="flex gap-2"
                onSubmit={(e) => {
                  e.preventDefault();
                  if (draft.trim()) void pick(qi, { text: draft });
                }}
              >
                <input
                  lang={language}
                  value={draft}
                  disabled={done || busy === qi}
                  maxLength={200}
                  onChange={(e) => setDrafts((d) => ({ ...d, [qi]: e.target.value }))}
                  aria-label={`${t.typeAnswer}: ${q.question}`}
                  placeholder={t.typeAnswer}
                  className="min-h-11 min-w-0 flex-1 rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-950"
                />
                <button type="submit" disabled={done || busy === qi || !draft.trim()} className="min-h-11 rounded-xl bg-brand-500 px-3 text-sm font-semibold text-white disabled:opacity-50">
                  {t.check}
                </button>
              </form>
              {done && (
                <p className="flex items-center gap-1 text-sm text-emerald-700 dark:text-emerald-300">
                  <CheckCircle2 className="size-4 shrink-0" aria-label={t.right} /> <span lang={language}>{t.rightWas(q.options[st.right!] ?? "")}</span>
                </p>
              )}
              {!done && st.typedMisses > 0 && (
                <p className="flex flex-wrap items-center gap-2 text-sm text-rose-700 dark:text-rose-300">
                  <XCircle className="size-4 shrink-0" aria-label={t.wrong} /> {t.wrong}
                  <button type="button" onClick={() => void pick(qi, { text: "" }, true)} className="text-xs font-semibold text-brand-700 hover:underline dark:text-brand-200">
                    {t.reveal}
                  </button>
                </p>
              )}
            </fieldset>
          );
        }
        return (
          <fieldset key={qi} className="flex flex-col gap-2">
            <legend lang={language} className="mb-1 font-medium">{q.question}</legend>
            <div className="grid gap-2 sm:grid-cols-2">
              {q.options.map((option, oi) => {
                const right = st.right === oi;
                const wrong = st.wrong.includes(oi);
                return (
                  <button
                    key={oi}
                    type="button"
                    lang={language}
                    disabled={done || wrong || busy === qi}
                    onClick={() => void pick(qi, { choice: oi })}
                    className={`flex min-h-11 items-center justify-between gap-2 rounded-xl border px-3 py-2 text-left text-sm ${
                      right
                        ? "border-emerald-500 bg-emerald-50 dark:bg-emerald-950/40"
                        : wrong
                          ? "border-rose-400 bg-rose-50 text-rose-800 dark:bg-rose-950/40 dark:text-rose-200"
                          : "border-slate-200 hover:border-brand-500 dark:border-slate-700"
                    }`}
                  >
                    {option}
                    {right && <CheckCircle2 className="size-4 shrink-0 text-emerald-600" aria-label={t.right} />}
                    {wrong && <XCircle className="size-4 shrink-0" aria-label={t.wrong} />}
                  </button>
                );
              })}
            </div>
            {!done && st.wrong.length > 0 && (
              <button type="button" onClick={() => void pick(qi, { choice: st.wrong[0] ?? 0 }, true)} className="self-start text-xs font-semibold text-brand-700 hover:underline dark:text-brand-200">
                {t.reveal}
              </button>
            )}
          </fieldset>
        );
      })}
      {failed && <Notice tone="error">{cs.common.error}</Notice>}
    </section>
  );
}

/** One story, read line by line. Ungraded: no questions are scored and nothing is recorded. */
/** Reading text size, remembered per device (a family shares tablets: children and grandparents). */
const SIZES = { s: "text-base", m: "text-lg", l: "text-2xl" } as const;
type Size = keyof typeof SIZES;
const SIZE_KEY = "polyflow.library.size";

type Neighbour = { slug: string; title: string } | null;

// Session caches (per acting profile and language). The texts are static per deployment, so a
// story read once opens instantly when the learner comes back to it or pages back and forth, and
// the shelf paints from memory while a fresh copy loads in the background.
const STORIES = new Map<string, LibraryStory>();
const PENDING = new Map<string, Promise<LibraryStory>>();
const LIBRARIES = new Map<string, StoryLibrary>();
function loadStory(key: string, language: Language, slug: string): Promise<LibraryStory> {
  const hit = STORIES.get(key);
  if (hit) return Promise.resolve(hit);
  let p = PENDING.get(key);
  if (!p) {
    p = getLibraryStory(language, slug)
      .then((s) => {
        STORIES.set(key, s);
        return s;
      })
      .finally(() => PENDING.delete(key));
    PENDING.set(key, p);
  }
  return p;
}

function Reader({
  profile,
  typed,
  language,
  slug,
  onBack,
  read,
  onRead,
  prev,
  next,
  onOpen,
}: {
  profile: string;
  typed: boolean;
  language: Language;
  slug: string;
  onBack: () => void;
  read: boolean;
  onRead: () => void;
  prev: Neighbour;
  next: Neighbour;
  onOpen: (slug: string) => void;
}) {
  const cacheKey = `${profile}:${language}:${slug}`;
  const [story, setStory] = useState<LibraryStory | null>(() => STORIES.get(cacheKey) ?? null);
  // "missing": this story is not available here (unknown, or hidden by the content gate).
  const [failed, setFailed] = useState<false | "missing" | "error">(false);
  const [attempt, setAttempt] = useState(0);
  const [showCs, setShowCs] = useState(false);
  const [size, setSizeState] = useState<Size>("m");
  useEffect(() => {
    try {
      const v = window.localStorage.getItem(SIZE_KEY);
      if (v === "s" || v === "m" || v === "l") setSizeState(v);
    } catch {
      /* default size */
    }
  }, []);
  const setSize = (v: Size) => {
    setSizeState(v);
    try {
      window.localStorage.setItem(SIZE_KEY, v);
    } catch {
      /* this visit only */
    }
  };
  // Scaffolding between "no help" and "everything translated": reveal one line's Czech at a time.
  const [revealed, setRevealed] = useState<Set<number>>(new Set());
  const toggleLine = (i: number) =>
    setRevealed((prev) => {
      const next = new Set(prev);
      if (next.has(i)) next.delete(i);
      else next.add(i);
      return next;
    });
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
  // Reader keys: P read aloud / stop, T translation, N/→ next story, B/← previous, Esc library.
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.defaultPrevented || e.ctrlKey || e.metaKey || e.altKey || e.repeat || isTypingTarget(e.target)) return;
      const actions: Record<string, () => void> = {
        KeyP: () => (reading === null ? void readFrom(0) : stopReading()),
        KeyT: () => setShowCs((v) => !v),
        KeyN: () => next && onOpen(next.slug),
        ArrowRight: () => next && onOpen(next.slug),
        KeyB: () => prev && onOpen(prev.slug),
        ArrowLeft: () => prev && onOpen(prev.slug),
        Escape: onBack,
      };
      const run = actions[e.code];
      if (run && story) {
        e.preventDefault();
        run();
      }
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [reading, readFrom, stopReading, next, prev, onOpen, onBack, story]);
  // Leaving the story stops its voice.
  useEffect(() => () => {
    run.current += 1;
    stop();
  }, []);
  useEffect(() => {
    let live = true;
    const cached = STORIES.get(cacheKey);
    setStory(cached ?? null);
    setFailed(false);
    if (cached) return;
    loadStory(cacheKey, language, slug)
      .then((s) => live && setStory(s))
      .catch((e) => live && setFailed(e instanceof ApiError && e.status === 404 ? "missing" : "error"));
    return () => {
      live = false;
    };
  }, [cacheKey, language, slug, attempt]);
  // Once this story is on screen, fetch the next one quietly: "Další" then opens without a wait.
  // Only the text is prefetched; read-aloud audio is generated on demand.
  const nextSlug = next?.slug;
  useEffect(() => {
    if (!story || !nextSlug) return;
    const id = window.setTimeout(() => {
      loadStory(`${profile}:${language}:${nextSlug}`, language, nextSlug).catch(() => undefined);
    }, 400);
    return () => window.clearTimeout(id);
  }, [story, nextSlug, profile, language]);

  return (
    <article className="flex flex-col gap-4">
      <button type="button" onClick={onBack} className="inline-flex items-center gap-1 self-start text-sm font-semibold text-brand-700 hover:underline dark:text-brand-200">
        <ArrowLeft className="size-4" aria-hidden /> {t.back}
      </button>
      {failed === "missing" && <Notice>{t.storyMissing}</Notice>}
      {failed === "error" && <RetryNotice text={t.storyFailed} onRetry={() => setAttempt((n) => n + 1)} />}
      {!story && !failed && (
        <div aria-busy className="flex flex-col gap-3">
          <Skeleton lines={2} className="max-w-sm" />
          <div className="rounded-2xl border border-slate-200 p-4 dark:border-slate-800"><Skeleton lines={6} /></div>
        </div>
      )}
      {story && (
        <>
          <header>
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              {story.level} · {t.kinds[story.kind]}
            </p>
            <h2 lang={language} className="text-2xl font-bold">{story.title}</h2>
            <p className="text-sm text-slate-500">{story.title_cs}</p>
            {story.review_status === "unreviewed" && <p className="mt-1 text-xs text-amber-700 dark:text-amber-300">{t.unreviewed}</p>}
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
              title={showCs ? t.hideCs : t.showCs}
              className="inline-flex min-h-11 min-w-11 items-center justify-center gap-2 rounded-xl bg-slate-100 px-3 py-2 text-sm font-medium dark:bg-slate-800"
            >
              <Languages className="size-4" aria-hidden /> <span className="max-sm:sr-only">{showCs ? t.hideCs : t.showCs}</span>
            </button>
            <SlowToggle />
            <div role="radiogroup" aria-label={t.sizeLabel} className="flex overflow-hidden rounded-xl border border-slate-200 dark:border-slate-700">
              {(["s", "m", "l"] as const).map((v) => (
                <button
                  key={v}
                  type="button"
                  role="radio"
                  aria-checked={size === v}
                  aria-label={t.sizes[v]}
                  onClick={() => setSize(v)}
                  className={`min-h-11 min-w-11 px-2 font-semibold ${v === "s" ? "text-xs" : v === "m" ? "text-sm" : "text-lg"} ${size === v ? "bg-slate-800 text-white dark:bg-slate-200 dark:text-slate-900" : ""}`}
                >
                  A
                </button>
              ))}
            </div>
            <Link href={`/shadowing?story=${encodeURIComponent(story.slug)}`} title={t.shadowThis} className="inline-flex min-h-11 min-w-11 items-center justify-center gap-2 rounded-xl px-3 py-2 text-sm font-semibold text-brand-700 hover:bg-brand-500/10 dark:text-brand-200">
              <Waves className="size-4" aria-hidden /> <span className="max-sm:sr-only">{t.shadowThis}</span>
            </Link>
          </div>
          {noAudio && <Notice>{t.noAudio}</Notice>}
          {!showCs && <p className="-mt-2 text-xs text-slate-500 max-sm:hidden">{t.lineHelp}</p>}
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
          <ol className={`${SIZES[size]} flex flex-col gap-3 rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900`}>
            {story.lines.map((line, i) => (
              <li
                key={i}
                data-line={i}
                aria-current={reading === i ? "true" : undefined}
                className={`flex items-start gap-2 rounded-xl px-2 py-1 transition-colors ${reading === i ? "bg-brand-500/10" : ""}`}
              >
                <PlayButton url={libraryAudioUrl(language, slug, i)} size="sm" label={t.playLine(i + 1)} />
                <span className="flex min-w-0 flex-1 flex-col gap-0.5">
                  {line.speaker && <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">{line.speaker}</span>}
                  <GlossedLine text={line.text} stretch={story.stretch} language={language} />
                  {(showCs || revealed.has(i)) && <span lang="cs" className="text-sm text-slate-500">{line.cs}</span>}
                </span>
                {!showCs && (
                  <button
                    type="button"
                    onClick={() => toggleLine(i)}
                    aria-pressed={revealed.has(i)}
                    aria-label={t.lineCs(i + 1)}
                    className={`mt-1 shrink-0 rounded-md px-1.5 py-0.5 text-[11px] font-bold ${revealed.has(i) ? "bg-slate-700 text-white dark:bg-slate-200 dark:text-slate-900" : "bg-slate-100 text-slate-500 dark:bg-slate-800"}`}
                  >
                    CZ
                  </button>
                )}
              </li>
            ))}
          </ol>
          <Questions key={story.slug} language={language} slug={story.slug} questions={story.questions} onAllDone={onRead} typed={typed} />
          <button
            type="button"
            onClick={() => {
              onRead();
              onBack();
            }}
            className="inline-flex min-h-11 items-center gap-2 self-start rounded-xl border border-brand-500/50 px-4 py-2 text-sm font-semibold text-brand-700 hover:bg-brand-500/5 dark:text-brand-100"
          >
            <CheckCircle2 className="size-4" aria-hidden /> {read ? t.backRead : t.doneBack}
          </button>
          <nav aria-label={t.storyNav} className="flex flex-wrap justify-between gap-2 border-t border-slate-200 pt-3 text-sm dark:border-slate-800">
            {prev ? (
              <button type="button" onClick={() => onOpen(prev.slug)} className="inline-flex min-h-11 max-w-[48%] items-center gap-1 rounded-lg px-2 text-left text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800">
                <ChevronLeft className="size-4 shrink-0" aria-hidden /> <span lang={language} className="truncate">{prev.title}</span>
                <span className="hidden lg:inline"><Kbd>B</Kbd></span>
              </button>
            ) : <span />}
            {next && (
              <button type="button" onClick={() => onOpen(next.slug)} className="inline-flex min-h-11 max-w-[48%] items-center gap-1 rounded-lg px-2 text-right font-semibold text-brand-700 hover:bg-brand-500/10 dark:text-brand-200">
                <span lang={language} className="truncate">{next.title}</span> <ChevronRight className="size-4 shrink-0" aria-hidden />
                <span className="hidden lg:inline"><Kbd>N</Kbd></span>
              </button>
            )}
          </nav>
          <p className="hidden text-xs text-slate-500 lg:block">{t.keys}</p>
        </>
      )}
    </article>
  );
}

function Shelf({ library, stories: shown, filtered, onReset, onOpen, read, level: myLevel, estimate }: { library: StoryLibrary; stories: StoryLibrary["stories"]; filtered: boolean; onReset: () => void; onOpen: (slug: string) => void; read: Set<string>; level: CefrLevel | null; estimate: string | null }) {
  if (!library.stories.length) return <Notice>{t.empty}</Notice>;
  // Next to read: the first unread story at the learner's level, then the levels above it.
  const from = myLevel ? LEVELS.indexOf(myLevel) : 0;
  const next = LEVELS.slice(from)
    .flatMap((lvl) => library.stories.filter((x) => x.level === lvl))
    .find((x) => !read.has(x.slug));
  return (
    <div className="flex flex-col gap-5">
      {next && !filtered && (
        <section aria-labelledby="next-title" className="rounded-2xl border border-brand-500/40 bg-brand-500/5 p-4">
          <p id="next-title" className="text-xs font-semibold uppercase tracking-wide text-brand-700 dark:text-brand-200">
            {myLevel ? t.nextFor(myLevel) : t.nextStart}
          </p>
          <p lang={library.language} className="mt-1 text-xl font-bold">{next.title}</p>
          <p className="text-sm text-slate-600 dark:text-slate-300">{next.title_cs}</p>
          <p className="mt-1 text-xs text-slate-500">{estimate ?? t.noEstimate}</p>
          <button type="button" onClick={() => onOpen(next.slug)} className="mt-3 inline-flex min-h-11 items-center gap-2 rounded-xl bg-brand-500 px-4 py-2 font-semibold text-white hover:bg-brand-600">
            <BookOpenText className="size-5" aria-hidden /> {t.startReading}
          </button>
        </section>
      )}
      {LEVELS.map((level) => {
        const stories = shown.filter((s) => s.level === level);
        if (!stories.length) return null;
        return (
          <section key={level} aria-labelledby={`level-${level}`}>
            <h2 id={`level-${level}`} className="mb-2 flex flex-wrap items-baseline justify-between gap-2 text-lg font-bold">
              {t.level(level, stories.length)}
              <span className="text-xs font-normal text-slate-500">{t.readCount(stories.filter((x) => read.has(x.slug)).length, stories.length)}</span>
            </h2>
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
                      {read.has(s.slug) && <CheckCircle2 className="size-3.5 text-emerald-600" aria-label={t.readMark} />}
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
      {filtered && shown.length === 0 && (
        <div className="flex flex-col items-start gap-2 rounded-2xl border border-dashed border-slate-300 p-4 text-sm dark:border-slate-700">
          <p>{t.noMatch}</p>
          <button type="button" onClick={onReset} className="font-semibold text-brand-700 hover:underline dark:text-brand-200">{t.resetFilters}</button>
        </div>
      )}
    </div>
  );
}

export default function StoryLibraryPage() {
  const me = useRequireMe();
  const language = me?.acting.active_language;
  const [library, setLibrary] = useState<StoryLibrary | null>(null);
  const [failed, setFailed] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const [slug, setSlugState] = useState<string | null>(null);
  const [read, markRead] = useReadMarks(me?.acting.id, language);
  const [estimate, setEstimate] = useState<{ level: string; source: "test" | "progress" } | null>(null);
  const [filters, setFiltersState] = useState<Filters>(NO_FILTERS);
  useEffect(() => setFiltersState(readFilters()), []);
  const setFilters = useCallback((f: Filters) => {
    setFiltersState(f);
    writeFilters(f);
  }, []);
  const filtered = filters.q.trim() !== "" || filters.level !== null || filters.kind !== null || filters.unread;
  const shown = library ? applyFilters(library.stories, filters, read) : [];
  // Previous/next follow the shelf the learner came from: the filtered list when it holds this
  // story, the whole library otherwise (e.g. opened from a link). The order is frozen when the
  // reader opens, so finishing a story under "Jen nepřečtené" does not reshuffle next/previous.
  const [trail, setTrail] = useState<string[] | null>(null);
  const shownKey = shown.map((x) => x.slug).join(",");
  useEffect(() => {
    if (!slug || !library) {
      setTrail(null);
      return;
    }
    setTrail((cur) => {
      if (cur?.includes(slug)) return cur;
      const fromShelf = shownKey ? shownKey.split(",") : [];
      return fromShelf.includes(slug) ? fromShelf : library.stories.map((x) => x.slug);
    });
  }, [slug, library, shownKey]);
  const bySlug = new Map((library?.stories ?? []).map((x) => [x.slug, x]));
  const order = trail ?? [];
  const at = slug ? order.indexOf(slug) : -1;
  const neighbour = (d: number): Neighbour => {
    const x = at >= 0 ? bySlug.get(order[at + d] ?? "") : undefined;
    return x ? { slug: x.slug, title: x.title } : null;
  };

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
    const key = `${me?.acting.id}:${language}`;
    const cached = LIBRARIES.get(key);
    setLibrary(cached ?? null);
    setFailed(false);
    getStoryLibrary(language)
      .then((l) => {
        LIBRARIES.set(key, l);
        if (live) setLibrary(l);
      })
      // A failed refresh keeps the shelf already on screen; only an empty start shows the error.
      .catch(() => live && !cached && setFailed(true));
    // The estimate only picks where to start; without it the shelf simply starts at A1.
    setEstimate(null);
    Promise.allSettled([getDiagnosticInfo(language), getProgress(language)]).then(([d, p]) => {
      if (!live) return;
      const test = d.status === "fulfilled" ? d.value.latest?.level : null;
      const prog = p.status === "fulfilled" ? p.value.cefr_level : null;
      setEstimate(test ? { level: test, source: "test" } : prog ? { level: prog, source: "progress" } : null);
    });
    return () => {
      live = false;
    };
  }, [language, me?.acting.id, attempt]);

  if (!me || !language) return <FullPageStatus text={cs.common.loading} />;
  return (
    <AppShell me={me}>
      <div className="mx-auto flex w-full max-w-4xl flex-col gap-4">
        {/* While a story is open the page header shrinks to its name: the intro and the language
            switch belong to the shelf, and on a phone they pushed the first line of text off screen. */}
        <header className={`flex flex-wrap items-end justify-between gap-3 ${slug ? "max-sm:hidden" : ""}`}>
          <div>
            <h1 className={`flex items-center gap-2 font-bold ${slug ? "text-lg" : "text-2xl"}`}>
              <Library className={slug ? "size-5 text-brand-500" : "size-6 text-brand-500"} aria-hidden /> {t.title}
            </h1>
            {!slug && (
              <>
                <p className="mt-1 hidden max-w-2xl text-sm text-slate-600 sm:block dark:text-slate-300">{t.intro}</p>
                <details className="mt-1 text-sm text-slate-600 sm:hidden dark:text-slate-300">
                  <summary className="cursor-pointer font-medium text-slate-500">{t.aboutLibrary}</summary>
                  <p className="mt-1">{t.intro}</p>
                </details>
              </>
            )}
          </div>
          {!slug && <LanguagePicker me={me} />}
        </header>
        {library?.review_status === "unreviewed" && !slug && <p className="text-xs text-amber-700 dark:text-amber-300">{t.unreviewed}</p>}
        {failed && <RetryNotice text={t.libraryFailed} onRetry={() => setAttempt((n) => n + 1)} />}
        {!library && !failed && (
          <div aria-busy className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 6 }, (_, i) => (
              <div key={i} className="rounded-xl border border-slate-200 p-3 dark:border-slate-800"><Skeleton lines={3} /></div>
            ))}
          </div>
        )}
        {library &&
          (slug ? (
            <Reader
              profile={String(me.acting.id)}
              typed={me.acting.settings.practice_difficulty === "hard"}
              key={`${language}:${slug}`}
              language={language}
              slug={slug}
              onBack={() => setSlug(null)}
              read={read.has(slug)}
              onRead={() => markRead(slug)}
              prev={neighbour(-1)}
              next={neighbour(1)}
              onOpen={setSlug}
            />
          ) : (
            <>
            {library.stories.length > 0 && <FilterBar filters={filters} onChange={setFilters} shown={shown.length} total={library.stories.length} />}
            <Shelf
              library={library}
              stories={shown}
              filtered={filtered}
              onReset={() => setFilters(NO_FILTERS)}
              onOpen={setSlug}
              read={read}
              level={estimate ? (READ_AT[estimate.level] ?? null) : null}
              estimate={estimate ? (estimate.source === "test" ? t.estimateTest(estimate.level) : t.estimateProgress(estimate.level)) : null}
            />
            </>
          ))}
        {library && library.source && <p className="text-xs text-slate-500">{t.provenance(library.source, library.license)}</p>}
        <Link href="/stories" className="self-start text-sm font-medium text-brand-700 hover:underline dark:text-brand-200">
          {cs.stories.title}
        </Link>
      </div>
    </AppShell>
  );
}
