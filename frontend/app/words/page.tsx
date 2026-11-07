"use client";

import { ArrowUpDown, BookMarked, CircleHelp, Clock, Download, FolderOpen, Layers, List, Search, X } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

import { AppShell, FullPageStatus, LanguagePicker } from "@/components/AppShell";
import { FlashcardSession } from "@/components/FlashcardSession";
import { Kbd, KeyHint } from "@/components/Kbd";
import { NoteEditor } from "@/components/NoteEditor";
import { WordCollectionControl } from "@/components/WordCollectionControl";
import { PlayButton, SlowToggle } from "@/components/PlayButton";
import { Button, Notice, RetryNotice, Skeleton } from "@/components/ui";
import { addWordsToCollection, type DeckScope, getWord, getWordGroups, listWordCollections, listWords, myWordAudioUrl, wordExportUrl, type WordCollection, type WordDetail, type WordGroups, type WordList, type WordKind, type WordScope, type WordSort, type WordStatus } from "@/lib/api";
import { useRequireMe } from "@/lib/auth";
import { useHotkeys } from "@/lib/keyboard";
import { genderClass } from "@/lib/gender";
import { cs, relativeFuture } from "@/lib/i18n/cs";

const t = cs.words;
const STATUSES: WordStatus[] = ["learning", "passive", "known", "mastered", "seen"];
const LADDER: WordStatus[] = ["seen", "learning", "passive", "known", "mastered"];
const PILL: Record<WordStatus, string> = {
  mastered: "bg-violet-100 text-violet-800 dark:bg-violet-950 dark:text-violet-200",
  known: "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-200",
  passive: "bg-sky-100 text-sky-800 dark:bg-sky-950 dark:text-sky-200",
  learning: "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-200",
  seen: "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300",
};
const PAGE = 60;
const MAX_PICK = 100; // the bulk-add and picked-deck endpoints take at most 100 ids
const SORTS: WordSort[] = ["rank", "review", "errors", "recent"];
const KINDS: WordKind[] = ["noun", "verb", "adj", "adv", "other"];
type Tab = "all" | "levels" | "topics";
const TABS: { id: Tab; label: string }[] = [
  { id: "levels", label: t.tabLevels },
  { id: "topics", label: t.tabTopics },
  { id: "all", label: t.tabAll },
];

function GroupCard({
  title,
  subtitle,
  mine,
  total,
  onFlashcards,
  onShow,
}: {
  title: string;
  subtitle?: string;
  mine: number;
  total: number;
  onFlashcards: () => void;
  onShow: () => void;
}) {
  const percent = total ? Math.round((mine / total) * 100) : 0;
  return (
    <li className="flex flex-col gap-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
      <div className="flex flex-col gap-0.5">
        <p className="text-lg font-bold">{title}</p>
        {subtitle && <p className="text-xs text-slate-500">{subtitle}</p>}
      </div>
      <div className="flex flex-col gap-1">
        <p className="text-sm tabular-nums text-slate-600 dark:text-slate-300">{mine ? t.met(mine, total) : t.nothingYet}</p>
        <div className="h-1.5 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800" aria-hidden>
          <div className="h-full rounded-full bg-emerald-500" style={{ width: `${percent}%` }} />
        </div>
      </div>
      <div className="mt-auto flex flex-wrap gap-2">
        <Button className="flex-1 !py-2 text-sm" disabled={!mine} onClick={onFlashcards}>
          <Layers className="size-4" aria-hidden /> {cs.flashcards.run}
        </Button>
        <Button variant="secondary" className="!py-2 text-sm" disabled={!mine} onClick={onShow}>
          <List className="size-4" aria-hidden /> {t.showWords}
        </Button>
      </div>
    </li>
  );
}

function when(iso: string | null): string {
  if (!iso) return "–";
  // Day rounding called a check due in 11 hours "now"; only a past date is due.
  return new Date(iso).getTime() <= Date.now() ? t.dueNow : relativeFuture(iso);
}

function EvidenceRow({ label, done, correct, days, needCorrect, needDays }: { label: string; done: boolean; correct: number; days: number; needCorrect: number; needDays: number }) {
  // Progress is the weaker of the two requirements, so a bar never looks full before both are met.
  const share = done ? 1 : Math.min(correct / needCorrect, days / needDays, 1);
  return (
    <li className="flex flex-col gap-1">
      <div className="flex items-baseline justify-between gap-2 text-sm">
        <span className="font-medium">{label}</span>
        <span className={`shrink-0 text-xs tabular-nums ${done ? "font-semibold text-emerald-600 dark:text-emerald-400" : "text-slate-500"}`}>
          {done ? t.evidenceDone : correct === 0 ? t.evidenceNone : t.evidenceTally(correct, needCorrect, days, needDays)}
        </span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800" aria-hidden>
        <div className={`h-full rounded-full ${done ? "bg-emerald-500" : "bg-sky-500"}`} style={{ width: `${Math.round(share * 100)}%` }} />
      </div>
    </li>
  );
}

function EvidenceBlock({ w }: { w: WordDetail }) {
  const e = w.evidence;
  return (
    <div className="flex flex-col gap-1.5">
      <p className="text-xs font-semibold text-slate-500">{t.evidenceTitle}</p>
      <ul className="flex flex-col gap-2">
        <EvidenceRow label={t.evidenceRecognition} done={w.passive_known} correct={e.recognition.correct} days={e.recognition.days} needCorrect={e.required_correct} needDays={e.required_days} />
        <EvidenceRow label={t.evidenceProduction} done={w.active_known} correct={e.production.correct} days={e.production.days} needCorrect={e.production_required_correct} needDays={e.production_required_days} />
      </ul>
      <p className="text-[0.7rem] text-slate-500">{t.evidenceHelp}</p>
    </div>
  );
}

function Highlight({ text, part }: { text: string; part: string | null }) {
  const at = part ? text.indexOf(part) : -1;
  if (!part || at < 0) return <>{text}</>;
  return (
    <>
      {text.slice(0, at)}
      <mark className="rounded bg-amber-100 px-0.5 not-italic text-inherit dark:bg-amber-500/25">{part}</mark>
      {text.slice(at + part.length)}
    </>
  );
}

function Article({ gender, lemma }: { gender: string | null; lemma: string }) {
  return (
    <>
      {gender && gender.length > 1 && <span className={`mr-1 font-semibold ${genderClass(gender)}`}>{gender}</span>}
      <span className={gender && gender.length === 1 ? genderClass(gender) : ""}>{lemma}</span>
    </>
  );
}

function Inspector({ id, onClose, onTopic }: { id: string; onClose: () => void; onTopic: (scope: WordScope) => void }) {
  const [w, setW] = useState<WordDetail | null>(null);
  const [failed, setFailed] = useState(false);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    let cancelled = false;
    setW(null);
    setFailed(false); // a failure belongs to one word; browsing on must not keep showing it
    getWord(id)
      .then((d) => !cancelled && setW(d))
      .catch(() => !cancelled && setFailed(true));
    return () => {
      cancelled = true;
    };
  }, [id, attempt]);
  return (
    <aside
      aria-label={t.detail}
      className="fixed inset-x-0 bottom-0 z-20 max-h-[80vh] overflow-y-auto rounded-t-3xl border border-slate-200 bg-white p-5 shadow-2xl motion-safe:animate-pop-in dark:border-slate-800 dark:bg-slate-900 lg:sticky lg:top-4 lg:inset-auto lg:max-h-none lg:rounded-3xl lg:shadow-sm"
    >
      <div className="flex items-start justify-between gap-2">
        <p className="text-xs uppercase tracking-wide text-slate-500">{t.detail}</p>
        <button type="button" onClick={onClose} aria-label={cs.common.close} className="rounded-full p-1 hover:bg-slate-100 dark:hover:bg-slate-800">
          <X className="size-5" aria-hidden />
        </button>
      </div>
      {failed && <RetryNotice text={t.detailFailed} onRetry={() => setAttempt((n) => n + 1)} />}
      {!w ? (
        !failed && <Skeleton lines={5} className="mt-2" />
      ) : (
        <div className="flex flex-col gap-4">
          <div className="flex items-center gap-2">
            <p className="text-3xl font-bold" lang={w.language}>
              <Article gender={w.gender} lemma={w.lemma} />
            </p>
            <PlayButton url={myWordAudioUrl(w.id)} label={cs.audio.playWord} hotkey />
            <KeyHint k="P" />
            <span className="ml-auto">
              <SlowToggle />
            </span>
          </div>
          <div>
            <p className="text-lg">{w.translation}</p>
            <p className="text-xs text-slate-500">
              {[w.pos, w.ipa && `/${w.ipa}/`, t.rank(w.rank)].filter(Boolean).join(" · ")}
            </p>
          </div>
          {w.example && (
            <div className="flex items-center gap-1 rounded-xl bg-slate-50 p-3 dark:bg-slate-800/60">
              <p className="flex-1 text-sm italic" lang={w.language}>
                {w.example}
              </p>
              <PlayButton url={myWordAudioUrl(w.id, "example")} size="sm" label={cs.audio.playSentence} />
            </div>
          )}
          {w.contexts.length > 0 && (
            <div className="flex flex-col gap-1.5">
              <p className="text-xs font-semibold text-slate-500">{t.contexts}</p>
              <ul className="flex flex-col gap-1.5">
                {w.contexts.map((c) => (
                  <li key={c.topic_id}>
                    <button
                      type="button"
                      onClick={() => onTopic({ kind: "topic", id: c.topic_id, label: c.title })}
                      className="flex w-full flex-col gap-0.5 rounded-xl border border-slate-200 p-2.5 text-left hover:border-brand-500 dark:border-slate-700"
                    >
                      <span className="text-sm font-semibold">{c.title}</span>
                      {c.line && (
                        <span className="text-sm italic" lang={w.language}>
                          <Highlight text={c.line} part={c.match} />
                        </span>
                      )}
                      {c.line_cs && <span className="text-xs text-slate-500">{c.line_cs}</span>}
                    </button>
                  </li>
                ))}
              </ul>
              <p className="text-[0.7rem] text-slate-500">{t.contextsHelp}</p>
            </div>
          )}
          <NoteEditor itemId={w.id} initial={w.note} />
          <WordCollectionControl itemId={w.id} language={w.language} />
          <div className="flex flex-col gap-1">
            <p className="text-xs font-semibold text-slate-500">{t.journey}</p>
            <ol className="grid grid-cols-5 gap-1">
              {LADDER.map((s) => {
                const reached = LADDER.indexOf(s) <= LADDER.indexOf(w.status);
                return (
                  <li
                    key={s}
                    className={`rounded-lg px-1 py-1.5 text-center text-[0.65rem] font-semibold ${reached ? PILL[s] : "bg-slate-50 text-slate-400 dark:bg-slate-800/40"}`}
                  >
                    {t.status[s]}
                  </li>
                );
              })}
            </ol>
          </div>
          <EvidenceBlock w={w} />
          <dl className="grid grid-cols-2 gap-2 text-sm">
            {[
              [t.correct, w.correct],
              [t.errors, w.errors],
              [t.nextReview, w.introduced_at ? when(w.next_review_at) : t.notYet],
              [t.streak, w.review_streak],
            ].map(([k, v]) => (
              <div key={String(k)} className="rounded-xl bg-slate-50 p-2 dark:bg-slate-800/60">
                <dt className="text-xs text-slate-500">{k}</dt>
                <dd className="font-semibold tabular-nums">{v}</dd>
              </div>
            ))}
          </dl>
          <div className="flex flex-col gap-1">
            <p className="text-xs font-semibold text-slate-500">{t.history}</p>
            {w.history.length === 0 ? (
              <p className="text-sm text-slate-500">{t.noHistory}</p>
            ) : (
              <ul className="flex flex-wrap gap-1.5">
                {[...w.history].reverse().map((h, i) => (
                  <li
                    key={i}
                    title={`${new Date(h.at).toLocaleString("cs-CZ")} · ${h.graded ? t.graded : t.practice}${h.error_tag ? ` · ${cs.feedback.errors[h.error_tag] ?? h.error_tag}` : ""}`}
                    className={`size-3.5 rounded-full ${h.correct ? "bg-emerald-500" : "bg-rose-500"} ${h.graded ? "" : "opacity-40"}`}
                  />
                ))}
              </ul>
            )}
            <p className="text-[0.7rem] text-slate-500">{t.historyHelp}</p>
          </div>
        </div>
      )}
    </aside>
  );
}

export default function WordsPage() {
  const me = useRequireMe();
  useHotkeys(); // P plays the open word (Alt+P from the search box)
  const language = me?.acting.active_language;
  const [q, setQ] = useState("");
  const [status, setStatus] = useState<WordStatus | null>(null);
  const [due, setDue] = useState(false);
  const [sort, setSort] = useState<WordSort>("rank");
  const [kind, setKind] = useState<WordKind | null>(null);
  const [data, setData] = useState<WordList | null>(null);
  const [more, setMore] = useState(false);
  const [failed, setFailed] = useState(false);
  const [listAttempt, setListAttempt] = useState(0);
  const [groupsAttempt, setGroupsAttempt] = useState(0);
  const [moreFailed, setMoreFailed] = useState(false);
  const [open, setOpen] = useState<string | null>(null);
  const [cursor, setCursor] = useState(0);
  const [collections, setCollections] = useState<WordCollection[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [targetCollection, setTargetCollection] = useState("");
  const [savingSelected, setSavingSelected] = useState(false);
  const [bulkNotice, setBulkNotice] = useState<{ text: string; error?: boolean } | null>(null);
  const search = useRef<HTMLInputElement>(null);
  const [tab, setTab] = useState<Tab>("levels");
  const [groups, setGroups] = useState<WordGroups | null>(null);
  const [groupsFailed, setGroupsFailed] = useState(false);
  const [scope, setScope] = useState<WordScope | null>(null);
  const [cards, setCards] = useState<DeckScope | null>(null);

  // Filters, tab, scope and the open word live in the URL so a reload, Back or a shared link restores the
  // same view. Topic labels need the group list, so a topic scope from the URL resolves once groups load.
  const [urlRead, setUrlRead] = useState(false);
  const pendingTopic = useRef<string | null>(null);
  const groupsFor = useRef<string | null>(null);
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const initialQuery = params.get("q");
    const initialWord = params.get("word");
    const initialTab = params.get("tab");
    const initialStatus = params.get("status");
    const level = params.get("level");
    const topic = params.get("topic");
    const filtered = Boolean(initialQuery || initialWord || initialStatus || params.get("due") || params.get("sort") || params.get("kind") || level || topic);
    if (filtered) setTab("all");
    else if (initialTab === "all" || initialTab === "levels" || initialTab === "topics") setTab(initialTab);
    if (initialQuery) setQ(initialQuery);
    if (initialWord) setOpen(initialWord);
    if (initialStatus && (STATUSES as string[]).includes(initialStatus)) setStatus(initialStatus as WordStatus);
    if (params.get("due") === "1") setDue(true);
    const initialSort = params.get("sort");
    if (initialSort && (SORTS as string[]).includes(initialSort)) setSort(initialSort as WordSort);
    const initialKind = params.get("kind");
    if (initialKind && (KINDS as string[]).includes(initialKind)) setKind(initialKind as WordKind);
    if (level) setScope({ kind: "level", key: level, label: t.level(level) });
    else if (topic) pendingTopic.current = topic;
    setUrlRead(true);
  }, []);
  useEffect(() => {
    if (!urlRead) return;
    const params = new URLSearchParams(window.location.search);
    const set = (k: string, v: string | null) => (v ? params.set(k, v) : params.delete(k));
    set("tab", tab === "levels" ? null : tab);
    set("q", tab === "all" ? q.trim() || null : null);
    set("status", tab === "all" ? status : null);
    set("due", tab === "all" && due ? "1" : null);
    set("sort", tab === "all" && sort !== "rank" ? sort : null);
    set("kind", tab === "all" ? kind : null);
    set("word", tab === "all" ? open : null);
    if (!pendingTopic.current) {
      set("level", tab === "all" && scope?.kind === "level" ? scope.key : null);
      set("topic", tab === "all" && scope?.kind === "topic" ? scope.id : null);
    }
    const qs = params.toString();
    const next = `${window.location.pathname}${qs ? `?${qs}` : ""}`;
    if (next !== `${window.location.pathname}${window.location.search}`) window.history.replaceState(window.history.state, "", next);
  }, [urlRead, tab, q, status, due, sort, kind, open, scope, groups]);

  useEffect(() => {
    if (!language) return;
    const ctrl = new AbortController();
    const timer = setTimeout(() => {
      listWords(language, { q, status, due, limit: PAGE, scope, sort, kind }, ctrl.signal)
        .then((d) => {
          setData(d);
          setCursor(0);
          setFailed(false);
        })
        .catch((e) => e?.name !== "AbortError" && setFailed(true));
    }, 180);
    return () => {
      clearTimeout(timer);
      ctrl.abort();
    };
  }, [language, q, status, due, scope, sort, kind, me?.acting.id, listAttempt]);

  // Another language or profile: never show the previous one's words while the new list loads.
  useEffect(() => {
    setData(null);
    setFailed(false);
  }, [language, me?.acting.id]);

  useEffect(() => {
    if (!language) return;
    const ctrl = new AbortController();
    const key = `${me?.acting.id}:${language}`;
    // A scope belongs to one language; only drop it when the language or profile actually changes, not on
    // the first load where it may have come from the URL.
    if (groupsFor.current !== null && groupsFor.current !== key) {
      setScope(null);
      pendingTopic.current = null;
    }
    groupsFor.current = key;
    setGroups(null);
    setGroupsFailed(false);
    setCards(null);
    getWordGroups(language, ctrl.signal)
      .then((g) => {
        setGroups(g);
        const wanted = pendingTopic.current;
        if (wanted) {
          pendingTopic.current = null;
          const topic = g.topics.find((item) => item.id === wanted);
          if (topic) setScope({ kind: "topic", id: topic.id, label: topic.title });
        }
      })
      .catch((e) => e?.name !== "AbortError" && setGroupsFailed(true));
    return () => ctrl.abort();
  }, [language, me?.acting.id, groupsAttempt]);

  useEffect(() => {
    if (!language) return;
    setSelected([]);
    setTargetCollection("");
    setBulkNotice(null);
    listWordCollections(language).then(setCollections).catch(() => setCollections([]));
  }, [language, me?.acting.id]);

  const loadMore = useCallback(async () => {
    if (!language || !data) return;
    setMore(true);
    setMoreFailed(false);
    try {
      const next = await listWords(language, { q, status, due, offset: data.items.length, limit: PAGE, scope, sort, kind });
      setData({ ...data, items: [...data.items, ...next.items] });
    } catch {
      setMoreFailed(true);
    } finally {
      setMore(false);
    }
  }, [language, data, q, status, due, scope, sort, kind]);

  // Moving the highlight with the inspector open browses word by word: the card follows the row.
  function move(delta: number) {
    const items = data?.items ?? [];
    if (!items.length) return;
    const next = Math.max(0, Math.min(cursor + delta, items.length - 1));
    setCursor(next);
    if (open) setOpen(items[next]!.id);
    // Keep keyboard focus on the highlighted row when it was on a row already.
    if ((document.activeElement as HTMLElement | null)?.dataset.wordRow !== undefined) {
      document.querySelector<HTMLElement>(`#word-row-${next} [data-word-row]`)?.focus();
    }
  }

  function onListKey(e: React.KeyboardEvent) {
    const target = e.target as HTMLElement;
    if (target.closest("input, select, textarea") || (target.closest("button") && target.dataset.wordRow === undefined)) return;
    if (!data?.items.length) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      move(1);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      move(-1);
    } else if (e.key === "Enter") {
      e.preventDefault();
      setOpen(data.items[cursor]!.id);
    } else if (e.key === "Escape") setOpen(null);
  }

  // The search box drives the list like a combobox: ↑/↓ move the highlighted row, Enter opens it and
  // Escape clears the search (a second Escape closes the open word).
  function onSearchKey(e: React.KeyboardEvent<HTMLInputElement>) {
    const items = data?.items ?? [];
    if (e.key === "ArrowDown" && items.length) {
      e.preventDefault();
      move(1);
    } else if (e.key === "ArrowUp" && items.length) {
      e.preventDefault();
      move(-1);
    } else if (e.key === "Enter" && items[cursor]) {
      e.preventDefault();
      setOpen(items[cursor]!.id);
    } else if (e.key === "Escape") {
      e.preventDefault();
      if (q) setQ("");
      else setOpen(null);
    }
  }

  async function saveSelected() {
    if (!targetCollection || selected.length === 0) return;
    setSavingSelected(true);
    setBulkNotice(null);
    try {
      const result = await addWordsToCollection(targetCollection, selected);
      setBulkNotice({ text: result.added ? t.bulkAdded(result.added, selected.length) : t.bulkNoop });
      setSelected([]);
      if (language) setCollections(await listWordCollections(language));
    } catch {
      setBulkNotice({ text: t.bulkFailed, error: true });
    } finally {
      setSavingSelected(false);
    }
  }

  useEffect(() => {
    document.getElementById(`word-row-${cursor}`)?.scrollIntoView({ block: "nearest" });
  }, [cursor]);

  if (!me) return <FullPageStatus text={cs.common.loading} />;
  // Status counts follow search, due and scope, so `total` is "matching words" and adds up with the chips.
  const total = data ? Object.values(data.counts).reduce((a, b) => a + b, 0) : 0;
  const narrowed = Boolean(q.trim() || status || due || kind || scope);
  return (
    <AppShell me={me}>
      <div className="flex flex-col gap-4">
        <div className="flex flex-wrap items-end justify-between gap-2">
          <div>
            <h1 className="flex items-center gap-2 text-xl font-bold">
              <BookMarked className="size-6 text-brand-500" aria-hidden />
              {t.title}
            </h1>
            <p className="text-sm text-slate-600 dark:text-slate-300">{t.intro}</p>
          </div>
          <LanguagePicker me={me} />
          <Link href="/collections" className="inline-flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium hover:border-brand-500 dark:border-slate-700">
            <FolderOpen className="size-4" aria-hidden /> {cs.collections.link}
          </Link>
        </div>
        {cards && language ? (
          <FlashcardSession key={`${cards.kind}:${cards.label}`} language={language} scope={cards} onClose={() => setCards(null)} />
        ) : (
          <>
            <div role="tablist" aria-label={t.browseBy} className="flex flex-wrap gap-1 rounded-2xl bg-slate-100 p-1 dark:bg-slate-800/60">
              {TABS.map((item) => (
                <button
                  key={item.id}
                  id={`words-tab-${item.id}`}
                  type="button"
                  role="tab"
                  aria-selected={tab === item.id}
                  aria-controls={`words-panel-${item.id}`}
                  onClick={() => setTab(item.id)}
                  className={`flex-1 rounded-xl px-3 py-2 text-sm font-semibold outline-none focus-visible:ring-2 focus-visible:ring-brand-500 ${
                    tab === item.id ? "bg-white text-brand-600 shadow-sm dark:bg-slate-900 dark:text-brand-50" : "text-slate-600 hover:bg-white/60 dark:text-slate-300 dark:hover:bg-slate-900/60"
                  }`}
                >
                  {item.label}
                </button>
              ))}
            </div>

            {tab !== "all" && (
              <div id={`words-panel-${tab}`} role="tabpanel" aria-labelledby={`words-tab-${tab}`} className="flex flex-col gap-3">
                {groupsFailed && <RetryNotice text={t.groupsFailed} onRetry={() => setGroupsAttempt((n) => n + 1)} />}
                {!groups && !groupsFailed && (
                  <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                    {[0, 1, 2].map((i) => (
                      <Skeleton key={i} lines={3} className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900" />
                    ))}
                  </div>
                )}
                {groups && tab === "levels" && (
                  <>
                    <ul className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                      {groups.levels.map((level) => {
                        const label = t.level(level.key);
                        const pick: WordScope = { kind: "level", key: level.key, label };
                        return (
                          <GroupCard
                            key={level.key}
                            title={label}
                            subtitle={t.levelRanks(level.first_rank, level.last_rank)}
                            mine={level.mine}
                            total={level.total}
                            onFlashcards={() => setCards(pick)}
                            onShow={() => {
                              setScope(pick);
                              setTab("all");
                            }}
                          />
                        );
                      })}
                    </ul>
                    <p className="text-xs text-slate-500">{t.levelNote}</p>
                  </>
                )}
                {groups && tab === "topics" && (
                  groups.topics.length === 0 ? (
                    <Notice>{t.noTopics}</Notice>
                  ) : (
                    <>
                      <ul className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                        {groups.topics.map((topic) => {
                          const pick: WordScope = { kind: "topic", id: topic.id, label: topic.title };
                          return (
                            <GroupCard
                              key={topic.id}
                              title={topic.title}
                              mine={topic.mine}
                              total={topic.total}
                              onFlashcards={() => setCards(pick)}
                              onShow={() => {
                                setScope(pick);
                                setTab("all");
                              }}
                            />
                          );
                        })}
                      </ul>
                      <p className="text-xs text-slate-500">{t.topicsNote}</p>
                    </>
                  )
                )}
              </div>
            )}

            <div id="words-panel-all" role="tabpanel" aria-labelledby="words-tab-all" hidden={tab !== "all"} className="flex flex-col gap-4">
            {scope && (
              <div className="flex flex-wrap items-center gap-2">
                <span className="inline-flex items-center gap-2 rounded-full bg-brand-500/10 px-3 py-1.5 text-sm font-semibold text-brand-600 dark:text-brand-50">
                  {t.scoped(scope.label)}
                  <button type="button" onClick={() => setScope(null)} aria-label={t.clearScope} className="rounded-full p-0.5 hover:bg-brand-500/20">
                    <X className="size-3.5" aria-hidden />
                  </button>
                </span>
                <Button variant="secondary" className="!py-1.5 text-sm" onClick={() => setCards(scope)}>
                  <Layers className="size-4" aria-hidden /> {cs.flashcards.run}
                </Button>
              </div>
            )}
            {(total > 0 || narrowed) && me.acting.active_language && (
              <details className="group self-start text-sm">
                <summary className="inline-flex cursor-pointer items-center gap-1.5 rounded-lg px-2 py-1 font-medium text-brand-600 hover:bg-brand-500/10 dark:text-brand-50">
                  <Download className="size-4" aria-hidden />
                  {t.export}
                </summary>
                <div className="mt-2 flex max-w-md flex-col gap-2 rounded-xl border border-slate-200 p-3 dark:border-slate-800">
                  <p className="text-xs text-slate-500">{t.exportHelp}</p>
                  <div className="flex gap-2">
                    <a className="rounded-lg bg-slate-100 px-3 py-1.5 font-medium hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700" href={wordExportUrl(me.acting.active_language, "csv")} download>
                      {t.exportCsv}
                    </a>
                    <a className="rounded-lg bg-slate-100 px-3 py-1.5 font-medium hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700" href={wordExportUrl(me.acting.active_language, "anki")} download>
                      {t.exportAnki}
                    </a>
                  </div>
                </div>
              </details>
            )}
            <div className="grid gap-4 lg:grid-cols-[1fr_22rem]">
              <div className="flex min-w-0 flex-col gap-3" onKeyDown={onListKey}>
                <label className="flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-3 focus-within:border-brand-500 focus-within:ring-2 focus-within:ring-brand-500/30 dark:border-slate-700 dark:bg-slate-900">
                  <Search className="size-5 text-slate-400" aria-hidden />
                  <input
                    ref={search}
                    type="search"
                    data-page-search
                    value={q}
                    onChange={(e) => setQ(e.target.value)}
                    onKeyDown={onSearchKey}
                    aria-controls="word-list"
                    aria-activedescendant={data?.items.length ? `word-row-${cursor}` : undefined}
                    placeholder={t.search}
                    aria-label={t.search}
                    className="w-full bg-transparent py-3 outline-none"
                  />
                  <span className="hidden shrink-0 text-xs text-slate-400 lg:inline">
                    <Kbd>/</Kbd> <Kbd>↑</Kbd> <Kbd>↓</Kbd> <Kbd>Enter</Kbd>
                  </span>
                </label>
                <div className="flex flex-wrap gap-1">
                  <button
                    type="button"
                    aria-pressed={status === null}
                    onClick={() => setStatus(null)}
                    className={`rounded-full px-3 py-1 text-sm font-medium ${status === null ? "bg-brand-500 text-white" : "bg-slate-100 dark:bg-slate-800"}`}
                  >
                    {t.all} {total}
                  </button>
                  {STATUSES.map((s) => (
                    <button
                      key={s}
                      type="button"
                      aria-pressed={status === s}
                      onClick={() => setStatus(status === s ? null : s)}
                      className={`rounded-full px-3 py-1 text-sm font-medium ${status === s ? "ring-2 ring-brand-500" : ""} ${PILL[s]}`}
                    >
                      {t.status[s]} {data?.counts[s] ?? 0}
                    </button>
                  ))}
                  <button
                    type="button"
                    aria-pressed={due}
                    onClick={() => setDue(!due)}
                    className={`inline-flex items-center gap-1 rounded-full px-3 py-1 text-sm font-medium ${due ? "bg-amber-500 text-white" : "bg-slate-100 dark:bg-slate-800"}`}
                  >
                    <Clock className="size-3.5" aria-hidden /> {t.dueOnly}
                  </button>
                  <label className="ml-auto inline-flex items-center gap-1.5 text-sm text-slate-600 dark:text-slate-300">
                    <ArrowUpDown className="size-4" aria-hidden />
                    <span className="sr-only sm:not-sr-only">{t.sortLabel}</span>
                    <select
                      value={sort}
                      onChange={(e) => setSort(e.target.value as WordSort)}
                      aria-label={t.sortLabel}
                      className="rounded-lg border border-slate-300 bg-white px-2 py-1 text-sm dark:border-slate-700 dark:bg-slate-900"
                    >
                      {SORTS.map((value) => (
                        <option key={value} value={value}>
                          {t.sorts[value]}
                        </option>
                      ))}
                    </select>
                  </label>
                </div>
                <details className="self-start text-sm">
                  <summary className="inline-flex cursor-pointer items-center gap-1.5 rounded-lg px-1 py-0.5 text-xs font-medium text-slate-500 hover:text-brand-600">
                    <CircleHelp className="size-3.5" aria-hidden /> {t.legendTitle}
                  </summary>
                  <dl className="mt-2 flex max-w-xl flex-col gap-1.5 rounded-xl border border-slate-200 p-3 dark:border-slate-800">
                    {LADDER.map((s) => (
                      <div key={s} className="flex items-start gap-2">
                        <dt className={`w-24 shrink-0 rounded-full px-2 py-0.5 text-center text-xs font-semibold ${PILL[s]}`}>{t.status[s]}</dt>
                        <dd className="text-xs text-slate-600 dark:text-slate-300">{t.legend[s]}</dd>
                      </div>
                    ))}
                    <div className="flex items-start gap-2">
                      <dt className="flex w-24 shrink-0 justify-center">
                        <Clock className="size-4 text-amber-500" aria-hidden />
                      </dt>
                      <dd className="text-xs text-slate-600 dark:text-slate-300">{t.legendDue}</dd>
                    </div>
                    {language && language !== "en" && (
                      <div className="flex items-start gap-2">
                        <dt className="w-24 shrink-0 text-center text-xs font-semibold">
                          {(language === "de" ? ["der", "die", "das"] : ["m", "f"]).map((g) => (
                            <span key={g} className={`mr-1 ${genderClass(g)}`}>
                              {g}
                            </span>
                          ))}
                        </dt>
                        <dd className="text-xs text-slate-600 dark:text-slate-300">{t.legendGender}</dd>
                      </div>
                    )}
                  </dl>
                </details>
                <div role="group" aria-label={t.kindLabel} className="-mx-1 flex gap-1 overflow-x-auto px-1 pb-0.5 [scrollbar-width:none]">
                  {KINDS.map((value) => (
                    <button
                      key={value}
                      type="button"
                      aria-pressed={kind === value}
                      onClick={() => setKind(kind === value ? null : value)}
                      className={`shrink-0 rounded-lg border px-2.5 py-1 text-xs font-medium ${
                        kind === value ? "border-brand-500 bg-brand-500/10 text-brand-600 dark:text-brand-50" : "border-slate-200 text-slate-600 hover:border-brand-500 dark:border-slate-700 dark:text-slate-300"
                      }`}
                    >
                      {t.kinds[value]}
                    </button>
                  ))}
                </div>
                {failed && <RetryNotice text={t.listFailed} onRetry={() => setListAttempt((n) => n + 1)} />}
                {!data && !failed && <Skeleton lines={6} className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900" />}
                {selected.length > 0 && (
                  <section aria-label={t.addSelected} className="flex flex-wrap items-center gap-2 rounded-2xl border border-brand-500/30 bg-brand-500/5 p-3">
                    <span className="mr-auto text-sm font-semibold">{t.selected(selected.length)}</span>
                    <Button variant="secondary" onClick={() => setCards({ kind: "picked", ids: selected, label: t.pickedDeck(selected.length) })}>
                      <Layers className="size-4" aria-hidden /> {t.practiseSelected}
                    </Button>
                    {collections.length ? (
                      <>
                        <label className="sr-only" htmlFor="bulk-collection">{t.selectCollection}</label>
                        <select id="bulk-collection" value={targetCollection} onChange={(e) => setTargetCollection(e.target.value)} className="rounded-lg border border-slate-300 bg-white px-2 py-2 text-sm dark:border-slate-700 dark:bg-slate-900">
                          <option value="">{t.selectCollection}</option>
                          {collections.map((collection) => <option key={collection.id} value={collection.id}>{collection.name} · {cs.collections.count(collection.count)}</option>)}
                        </select>
                        <Button disabled={!targetCollection || savingSelected} onClick={() => void saveSelected()}>{savingSelected ? cs.common.loading : t.addSelected}</Button>
                      </>
                    ) : (
                      <Link href="/collections" className="rounded-lg bg-brand-500 px-3 py-2 text-sm font-semibold text-white">{t.createCollection}</Link>
                    )}
                    <button type="button" onClick={() => setSelected([])} aria-label={cs.common.close} className="rounded-lg p-2 hover:bg-slate-100 dark:hover:bg-slate-800"><X className="size-4" aria-hidden /></button>
                  </section>
                )}
                {bulkNotice && <Notice tone={bulkNotice.error ? "error" : "ok"}>{bulkNotice.text}</Notice>}
                {data && data.items.length > 1 && (
                  <label className="inline-flex items-center gap-2 self-start pl-3 text-sm text-slate-600 dark:text-slate-300">
                    <input
                      type="checkbox"
                      className="size-4 accent-brand-600"
                      checked={data.items.every((w) => selected.includes(w.id))}
                      onChange={(e) => {
                        const shown = data.items.map((w) => w.id);
                        setSelected((current) =>
                          e.target.checked ? [...current, ...shown.filter((id) => !current.includes(id))].slice(0, MAX_PICK) : current.filter((id) => !shown.includes(id)),
                        );
                      }}
                    />
                    {t.selectShown(data.items.length)}
                  </label>
                )}
                {selected.length >= MAX_PICK && <p className="text-xs text-slate-500">{t.selectLimit}</p>}
                {data && data.items.length === 0 && <Notice>{narrowed ? t.noMatch : t.empty}</Notice>}
                <ul id="word-list" className="flex flex-col divide-y divide-slate-100 overflow-hidden rounded-2xl border border-slate-200 bg-white dark:divide-slate-800 dark:border-slate-800 dark:bg-slate-900">
                  {data?.items.map((w, i) => (
                    <li key={w.id} id={`word-row-${i}`}>
                      <div className="flex items-center">
                      <label className="flex shrink-0 items-center pl-3" title={t.selectWord(w.lemma)}>
                        <input type="checkbox" checked={selected.includes(w.id)} aria-label={t.selectWord(w.lemma)} disabled={!selected.includes(w.id) && selected.length >= MAX_PICK} onChange={(e) => setSelected((current) => e.target.checked ? [...current, w.id] : current.filter((id) => id !== w.id))} className="size-4 accent-brand-600" />
                      </label>
                      <button
                        type="button"
                        data-word-row
                        onClick={() => {
                          setCursor(i);
                          setOpen(w.id);
                        }}
                        className={`flex min-w-0 flex-1 items-center gap-3 px-4 py-2.5 text-left ${
                          open === w.id ? "bg-brand-500/10" : i === cursor ? "bg-slate-50 dark:bg-slate-800/60" : "hover:bg-slate-50 dark:hover:bg-slate-800/60"
                        }`}
                      >
                        <span className="w-10 shrink-0 text-right text-xs tabular-nums text-slate-400">{w.rank}</span>
                        <span className="min-w-0 flex-1">
                          <span className="block truncate font-semibold" lang={language}>
                            <Article gender={w.gender} lemma={w.lemma} />
                          </span>
                          <span className="block truncate text-sm text-slate-500">{w.translation}</span>
                        </span>
                        {sort === "review" && !w.due && w.next_review_at && <span className="shrink-0 text-xs text-slate-500">{when(w.next_review_at)}</span>}
                        {sort === "errors" && <span className={`shrink-0 text-xs tabular-nums ${w.errors ? "text-rose-600 dark:text-rose-400" : "text-slate-500"}`}>{t.rowErrors(w.errors)}</span>}
                        {w.due && <Clock className="size-4 text-amber-500" aria-label={t.dueNow} />}
                        <span className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-semibold ${PILL[w.status]}`}>{t.status[w.status]}</span>
                      </button>
                      <span className="shrink-0 pr-2">
                        <PlayButton url={myWordAudioUrl(w.id)} size="sm" label={t.playRow(w.lemma)} />
                      </span>
                      </div>
                    </li>
                  ))}
                </ul>
                {moreFailed && <RetryNotice text={t.moreFailed} onRetry={() => void loadMore()} />}
                {data && data.items.length < data.total && !moreFailed && (
                  <Button variant="secondary" disabled={more} onClick={() => void loadMore()}>
                    {more ? cs.common.loading : t.more(data.total - data.items.length)}
                  </Button>
                )}
              </div>
              <div>
                {open ? (
                  <Inspector
                    id={open}
                    onClose={() => setOpen(null)}
                    onTopic={(pick) => {
                      setScope(pick);
                      setStatus(null);
                      setDue(false);
                      setQ("");
                    }}
                  />
                ) : (
                  <p className="hidden rounded-3xl border border-dashed border-slate-300 p-6 text-sm text-slate-500 dark:border-slate-700 lg:block">
                    {t.pick}
                  </p>
                )}
              </div>
            </div>
            </div>
          </>
        )}
      </div>
    </AppShell>
  );
}
