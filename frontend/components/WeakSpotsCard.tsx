"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { PlayButton } from "@/components/PlayButton";
import { Notice, Skeleton } from "@/components/ui";
import { getWeakSpots, myWordAudioUrl, type Language, type WeakSpots } from "@/lib/api";
import { cs } from "@/lib/i18n/cs";

const LIMIT = 5;

/** Unresolved mistakes from recent checks: words, grammar units and the kinds of mistake. */
export function WeakSpotsCard({ language }: { language: Language }) {
  const [data, setData] = useState<WeakSpots | null>(null);
  const [failed, setFailed] = useState(false);
  const [all, setAll] = useState(false);
  useEffect(() => {
    let cancelled = false;
    setData(null);
    setFailed(false);
    getWeakSpots(language)
      .then((d) => !cancelled && setData(d))
      .catch(() => !cancelled && setFailed(true));
    return () => {
      cancelled = true;
    };
  }, [language]);

  if (failed) return <Notice tone="error">{cs.common.error}</Notice>;
  if (!data) return <Skeleton lines={4} />;
  const empty = !data.words.length && !data.units.length;
  // The worst few first (the API orders by errors); the rest on request, so the panel stays short.
  const words = all ? data.words : data.words.slice(0, LIMIT);
  return (
    <div className="flex flex-col gap-3 text-sm">
      <p className="text-slate-600 dark:text-slate-300">{cs.weak.help(data.window_days)}</p>
      {empty && <Notice tone="ok">{cs.weak.none}</Notice>}
      {data.words.length > 0 && (
        <section className="flex flex-col gap-1">
          <h3 className="font-semibold">{cs.weak.words}</h3>
          <ul className="divide-y divide-slate-200 rounded-xl border border-slate-200 dark:divide-slate-800 dark:border-slate-800">
            {words.map((w) => (
              <li key={w.item_id} className="flex items-center gap-2 px-2 py-1.5">
                <PlayButton url={myWordAudioUrl(w.item_id)} size="sm" />
                <Link
                  href={`/words?word=${encodeURIComponent(w.item_id)}`}
                  aria-label={cs.weak.open(w.lemma)}
                  className="flex min-w-0 flex-1 flex-wrap items-baseline justify-between gap-x-2 rounded-lg px-1 py-0.5 hover:bg-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 dark:hover:bg-slate-800"
                >
                  <span className="font-medium" lang={language}>
                    {language === "de" && w.gender ? `${w.gender} ` : ""}
                    {w.lemma}
                  </span>
                  <span className="text-slate-500" lang="cs">
                    {w.translation}
                  </span>
                  <span className="w-full text-xs text-slate-500">
                    {cs.weak.errors(w.errors)}
                    {w.tags.length > 0 && ` · ${w.tags.map((t) => cs.feedback.errors[t] ?? t).join(", ")}`}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
          {data.words.length > LIMIT && (
            <button
              type="button"
              onClick={() => setAll((v) => !v)}
              aria-expanded={all}
              className="self-start rounded-lg px-2 py-1 text-sm font-medium text-brand-600 hover:bg-brand-500/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 dark:text-brand-50"
            >
              {all ? cs.weak.showFewer : cs.weak.showAll(data.words.length)}
            </button>
          )}
        </section>
      )}
      {data.units.length > 0 && (
        <section className="flex flex-col gap-1">
          <h3 className="font-semibold">{cs.weak.grammar}</h3>
          <ul className="flex flex-col gap-1">
            {data.units.map((u) => (
              <li key={u.id}>
                <Link href={`/grammar/${u.id}`} className="flex justify-between gap-2 rounded-lg px-2 py-1 hover:bg-slate-100 dark:hover:bg-slate-800">
                  <span>
                    <span className="mr-1 text-xs text-slate-500">{u.level}</span>
                    {u.title}
                  </span>
                  <span className="shrink-0 text-xs text-slate-500">{cs.weak.errors(u.errors)}</span>
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}
      {data.tags.length > 0 && (
        <section className="flex flex-col gap-1">
          <h3 className="font-semibold">{cs.weak.kinds}</h3>
          <ul className="flex flex-wrap gap-1">
            {data.tags.map(([tag, n]) => (
              <li key={tag} className="rounded-full bg-slate-100 px-2 py-0.5 text-xs dark:bg-slate-800">
                {cs.feedback.errors[tag] ?? tag}: <strong className="tabular-nums">{n}</strong>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
