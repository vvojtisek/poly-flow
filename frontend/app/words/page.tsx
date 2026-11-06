"use client";

import { BookMarked, Clock, Search, X } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { AppShell, FullPageStatus, LanguagePicker } from "@/components/AppShell";
import { Kbd } from "@/components/Kbd";
import { PlayButton } from "@/components/PlayButton";
import { Button, Notice } from "@/components/ui";
import { getWord, listWords, myWordAudioUrl, type WordDetail, type WordList, type WordStatus } from "@/lib/api";
import { useRequireMe } from "@/lib/auth";
import { genderClass } from "@/lib/gender";
import { cs } from "@/lib/i18n/cs";

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

function when(iso: string | null): string {
  if (!iso) return "–";
  const days = Math.round((new Date(iso).getTime() - Date.now()) / 86_400_000);
  if (days <= 0) return t.dueNow;
  return t.inDays(days);
}

function Article({ gender, lemma }: { gender: string | null; lemma: string }) {
  return (
    <>
      {gender && gender.length > 1 && <span className={`mr-1 font-semibold ${genderClass(gender)}`}>{gender}</span>}
      <span className={gender && gender.length === 1 ? genderClass(gender) : ""}>{lemma}</span>
    </>
  );
}

function Inspector({ id, onClose }: { id: string; onClose: () => void }) {
  const [w, setW] = useState<WordDetail | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    let cancelled = false;
    setW(null);
    getWord(id)
      .then((d) => !cancelled && setW(d))
      .catch(() => !cancelled && setFailed(true));
    return () => {
      cancelled = true;
    };
  }, [id]);
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
      {failed && <Notice tone="error">{cs.common.error}</Notice>}
      {!w ? (
        !failed && <p className="text-sm text-slate-500">{cs.common.loading}</p>
      ) : (
        <div className="flex flex-col gap-4">
          <div className="flex items-center gap-2">
            <p className="text-3xl font-bold" lang={w.language}>
              <Article gender={w.gender} lemma={w.lemma} />
            </p>
            <PlayButton url={myWordAudioUrl(w.id)} hotkey />
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
  const language = me?.acting.active_language;
  const [q, setQ] = useState("");
  const [status, setStatus] = useState<WordStatus | null>(null);
  const [due, setDue] = useState(false);
  const [data, setData] = useState<WordList | null>(null);
  const [more, setMore] = useState(false);
  const [failed, setFailed] = useState(false);
  const [open, setOpen] = useState<string | null>(null);
  const [cursor, setCursor] = useState(0);
  const search = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!language) return;
    const ctrl = new AbortController();
    const timer = setTimeout(() => {
      listWords(language, { q, status, due, limit: PAGE }, ctrl.signal)
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
  }, [language, q, status, due, me?.acting.id]);

  const loadMore = useCallback(async () => {
    if (!language || !data) return;
    setMore(true);
    try {
      const next = await listWords(language, { q, status, due, offset: data.items.length, limit: PAGE });
      setData({ ...data, items: [...data.items, ...next.items] });
    } finally {
      setMore(false);
    }
  }, [language, data, q, status, due]);

  function onListKey(e: React.KeyboardEvent) {
    if (!data?.items.length) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setCursor((c) => Math.min(c + 1, data.items.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setCursor((c) => Math.max(c - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      setOpen(data.items[cursor]!.id);
    } else if (e.key === "Escape") setOpen(null);
  }

  useEffect(() => {
    document.getElementById(`word-row-${cursor}`)?.scrollIntoView({ block: "nearest" });
  }, [cursor]);

  if (!me) return <FullPageStatus text={cs.common.loading} />;
  const total = data ? Object.values(data.counts).reduce((a, b) => a + b, 0) : 0;
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
        </div>
        <div className="grid gap-4 lg:grid-cols-[1fr_22rem]">
          <div className="flex min-w-0 flex-col gap-3" onKeyDown={onListKey}>
            <label className="flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-3 focus-within:border-brand-500 focus-within:ring-2 focus-within:ring-brand-500/30 dark:border-slate-700 dark:bg-slate-900">
              <Search className="size-5 text-slate-400" aria-hidden />
              <input
                ref={search}
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder={t.search}
                aria-label={t.search}
                autoFocus
                className="w-full bg-transparent py-3 outline-none"
              />
              <span className="hidden text-xs text-slate-400 lg:inline">
                <Kbd>↑</Kbd> <Kbd>↓</Kbd> <Kbd>Enter</Kbd>
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
            </div>
            {failed && <Notice tone="error">{cs.common.error}</Notice>}
            {data && data.items.length === 0 && <Notice>{total === 0 ? t.empty : t.noMatch}</Notice>}
            <ul className="flex flex-col divide-y divide-slate-100 overflow-hidden rounded-2xl border border-slate-200 bg-white dark:divide-slate-800 dark:border-slate-800 dark:bg-slate-900">
              {data?.items.map((w, i) => (
                <li key={w.id} id={`word-row-${i}`}>
                  <button
                    type="button"
                    onClick={() => {
                      setCursor(i);
                      setOpen(w.id);
                    }}
                    className={`flex w-full items-center gap-3 px-4 py-2.5 text-left ${
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
                    {w.due && <Clock className="size-4 text-amber-500" aria-label={t.dueNow} />}
                    <span className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-semibold ${PILL[w.status]}`}>{t.status[w.status]}</span>
                  </button>
                </li>
              ))}
            </ul>
            {data && data.items.length < data.total && (
              <Button variant="secondary" disabled={more} onClick={() => void loadMore()}>
                {t.more(data.total - data.items.length)}
              </Button>
            )}
          </div>
          <div>
            {open ? (
              <Inspector id={open} onClose={() => setOpen(null)} />
            ) : (
              <p className="hidden rounded-3xl border border-dashed border-slate-300 p-6 text-sm text-slate-500 dark:border-slate-700 lg:block">
                {t.pick}
              </p>
            )}
          </div>
        </div>
      </div>
    </AppShell>
  );
}
