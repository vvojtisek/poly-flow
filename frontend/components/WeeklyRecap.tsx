"use client";

import { CalendarCheck, TrendingDown, TrendingUp } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { Panel } from "@/components/Panel";
import { addWordsToCollection, createWordCollection, getRecap, type Language, type Recap } from "@/lib/api";
import { genderClass } from "@/lib/gender";
import { cs } from "@/lib/i18n/cs";

const t = cs.recap;
const pct = (x: number | null) => (x === null ? null : `${Math.round(x * 100)} %`);
const day = (iso: string) => new Date(iso + "T12:00:00").toLocaleDateString("cs-CZ", { day: "numeric", month: "numeric" });
const TARGET: Record<Recap["suggestion"], string> = {
  check_due: "/check",
  fix_mistakes: "/words",
  new_lesson: "/lesson",
  start_small: "/lesson",
  keep_going: "/practice",
};

/** Seven days at a glance, compared with the seven before; one suggested next step. */
export function WeeklyRecap({ language, className = "" }: { language: Language; className?: string }) {
  const [data, setData] = useState<Recap | null>(null);
  const [failed, setFailed] = useState(false);
  const [savingHardWords, setSavingHardWords] = useState(false);
  const [saveHardWordsOpen, setSaveHardWordsOpen] = useState(false);
  const [hardSetName, setHardSetName] = useState("");
  const [hardSetMessage, setHardSetMessage] = useState<{ text: string; error?: boolean } | null>(null);
  const [hardSetUrl, setHardSetUrl] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setData(null);
    getRecap(language)
      .then((r) => !cancelled && setData(r))
      .catch(() => !cancelled && setFailed(true));
    return () => {
      cancelled = true;
    };
  }, [language]);

  if (failed) return null; // the rest of the page still shows; the recap is a summary only
  if (!data) return null;
  const recap = data;
  const w = data.this_week;
  const quiet = w.active_days === 0;
  const acc = pct(w.accuracy);
  const before = pct(data.last_week.accuracy);
  const Trend = data.accuracy_trend === "up" ? TrendingUp : data.accuracy_trend === "down" ? TrendingDown : null;

  async function saveHardWords(event: React.FormEvent) {
    event.preventDefault();
    if (!hardSetName.trim() || recap.hard_words.length === 0) return;
    setSavingHardWords(true);
    setHardSetMessage(null);
    let created: string | null = null;
    try {
      const collection = await createWordCollection(language, hardSetName);
      created = collection.id;
      await addWordsToCollection(collection.id, recap.hard_words.map((word) => word.id));
      setHardSetUrl("/collections");
      setHardSetMessage({ text: t.hardSetSaved });
      setSaveHardWordsOpen(false);
    } catch {
      setHardSetUrl(created ? "/collections" : null);
      setHardSetMessage({ text: created ? t.hardSetPartial : t.hardSetFailed, error: true });
    } finally {
      setSavingHardWords(false);
    }
  }

  return (
    <Panel title={`${t.title} · ${t.range(day(data.from), day(data.to))}`} icon={CalendarCheck} className={className}>
      <div className="flex flex-col gap-4">
        {quiet ? (
          <p className="text-slate-600 dark:text-slate-300">{t.quiet}</p>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <div className="rounded-xl bg-slate-50 p-3 dark:bg-slate-800/60">
              <p className="text-2xl font-bold">{w.active_days}/7</p>
              <p className="text-xs text-slate-500">{t.days(w.active_days)}</p>
            </div>
            <div className="rounded-xl bg-slate-50 p-3 dark:bg-slate-800/60">
              <p className="text-2xl font-bold">{w.introduced}</p>
              <p className="text-xs text-slate-500">
                {t.introduced(w.introduced)} · {t.known(w.newly_known)}
              </p>
            </div>
            <div className="rounded-xl bg-slate-50 p-3 dark:bg-slate-800/60">
              <p className="text-2xl font-bold">{w.graded}</p>
              <p className="text-xs text-slate-500">
                {t.answers(w.graded)} · {t.practice(w.practice)}
              </p>
            </div>
            <div className="rounded-xl bg-slate-50 p-3 dark:bg-slate-800/60">
              <p className="flex items-center gap-1 text-2xl font-bold">
                {acc ?? "–"}
                {Trend && <Trend className={`size-5 ${data.accuracy_trend === "up" ? "text-emerald-600" : "text-amber-600"}`} aria-hidden />}
              </p>
              <p className="text-xs text-slate-500">
                {t.accuracy}
                {acc === null ? `: ${t.unknown}` : data.accuracy_trend ? `, ${t.trend[data.accuracy_trend]}` : before ? ` (${t.lastWeek(before)})` : ""}
              </p>
            </div>
          </div>
        )}
        {data.hard_words.length > 0 && (
          <section className="flex flex-col gap-2">
            <div className="flex flex-wrap items-center gap-2 text-sm">
              <span className="font-medium text-slate-500">{t.hard}:</span>
              {data.hard_words.map((h) => (
                <span key={h.id} className="rounded-lg bg-rose-50 px-2 py-1 dark:bg-rose-950/40">
                  <strong lang={language} className={genderClass(h.gender)}>{h.lemma}</strong>{" "}
                  <span className="text-slate-600 dark:text-slate-300">{h.translation}</span>{" "}
                  <span className="text-xs text-rose-700 dark:text-rose-300">{t.misses(h.misses)}</span>
                </span>
              ))}
            </div>
            {saveHardWordsOpen ? (
              <form onSubmit={(event) => void saveHardWords(event)} className="flex flex-wrap gap-2">
                <label htmlFor="hard-words-collection" className="sr-only">{cs.collections.name}</label>
                <input id="hard-words-collection" maxLength={60} required value={hardSetName} onChange={(event) => setHardSetName(event.target.value)} placeholder={t.hardSetName} className="min-w-48 flex-1 rounded-lg border border-slate-300 bg-transparent px-3 py-2 text-sm dark:border-slate-700" />
                <button type="submit" disabled={savingHardWords || !hardSetName.trim()} className="rounded-lg bg-brand-500 px-3 py-2 text-sm font-semibold text-white disabled:opacity-50">{savingHardWords ? cs.common.loading : t.hardSetSave}</button>
                <button type="button" disabled={savingHardWords} onClick={() => setSaveHardWordsOpen(false)} className="rounded-lg px-3 py-2 text-sm hover:bg-slate-100 dark:hover:bg-slate-800">{cs.common.close}</button>
              </form>
            ) : (
              <button type="button" onClick={() => { setHardSetName(t.hardSetName); setHardSetMessage(null); setSaveHardWordsOpen(true); }} className="self-start rounded-lg border border-brand-500/40 px-3 py-2 text-sm font-semibold text-brand-700 hover:bg-brand-500/5 dark:text-brand-100">{t.hardSetAction}</button>
            )}
            {hardSetMessage && <p role="status" className={`text-sm ${hardSetMessage.error ? "text-rose-700 dark:text-rose-300" : "text-emerald-700 dark:text-emerald-300"}`}>{hardSetMessage.text} {hardSetUrl && <Link href={hardSetUrl} className="font-semibold underline">{t.hardSetOpen}</Link>}</p>}
          </section>
        )}
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-brand-500/30 bg-brand-500/5 p-3">
          <div className="flex flex-col">
            <p className="font-semibold">{t.suggestion[data.suggestion]}</p>
            <p className="text-xs text-slate-500">{t.due(data.due_now, data.due_next_7_days)}</p>
          </div>
          <Link href={TARGET[data.suggestion]} className="rounded-xl bg-brand-500 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-600">
            {t.go[data.suggestion]}
          </Link>
        </div>
      </div>
    </Panel>
  );
}
